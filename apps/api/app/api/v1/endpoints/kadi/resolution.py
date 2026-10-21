"""Entity-resolution review, feedback and threshold calibration (#31, #88)."""

from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.auto_triggers import run_auto_triggers
from app.case_auth import require_case_access
from app.database import get_db
from app.kadi_resolution import (
    ALL_TYPES_SCOPE,
    DecisionAlreadyResolved,
    DecisionStale,
    apply_feedback,
    latest_calibration,
    recalibrate,
)
from app.models import (
    KadiCase,
    KadiResolutionDecision,
    KadiThresholdCalibration,
)
from kadi.resolution import RESOLVABLE_ENTITY_TYPES, ResolutionThresholds
from app.services.case_ingestion import (  # noqa: F401 — re-exported for existing importers
    DUPLICATE_DOCUMENT_LOG,
    MAX_TRACKED_STATUS_CASES,
    _document_already_ingested,
    _duplicate_event,
    _evict_stale_status_entries,
    _record_case_latency,
    _wrap_session,
    create_case_record,
    ingest_document_now,
    process_document_background,
    processing_status,
)
from app.services.case_purge import (  # noqa: F401 — re-exported for existing importers
    _purge_bimanyay_records_for_case,
    purge_case,
)
from app.api.v1.endpoints.kadi.schemas import (
    ResolutionDecisionResponse,
    ResolutionFeedbackRequest,
    CalibrationAttempt,
    ResolutionFeedbackResponse,
    _decision_response,
)
from app.api.v1.endpoints.kadi.loaders import _load_case_with_entities

logger = logging.getLogger("arogyarakshak.api.kadi")
router = APIRouter()


# --- Entity resolution: review and feedback (#31, #88) ------------------------

@router.get("/cases/{case_id}/resolutions", response_model=List[ResolutionDecisionResponse])
async def list_resolution_decisions(
    case_id: str,
    status_filter: Optional[str] = Query(
        None, alias="status", pattern="^(pending|auto_merged|confirmed|rejected|split|superseded)$"
    ),
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Entity-resolution decisions for this case. `status=pending` lists the "are these the
    same?" questions awaiting the user; `auto_merged` lists merges the user can dispute.

    Not consent-gated: like GET /cases/{case_id}, it only exposes Kadi's own context for
    the case, not another module's view of it (see app.consent). Still access-gated
    (app.case_auth) — every case-scoped route is, regardless of consent."""
    query = select(KadiResolutionDecision).where(KadiResolutionDecision.case_id == case_id)
    if status_filter:
        query = query.where(KadiResolutionDecision.status == status_filter)
    rows = (await db.execute(query.order_by(KadiResolutionDecision.created_at))).scalars().all()
    return [_decision_response(d) for d in rows]


@router.post(
    "/cases/{case_id}/resolutions/{decision_id}/feedback", response_model=ResolutionFeedbackResponse
)
async def submit_resolution_feedback(
    case_id: str,
    decision_id: str,
    body: ResolutionFeedbackRequest,
    _case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Applies the user's answer and records it as a calibration label.

    - pending + same_entity=true  -> the mention is folded into the existing entity
    - pending + same_entity=false -> both entities are kept
    - auto_merged + false         -> the merge is split back into its own entity
    """
    # apply_feedback needs entities eagerly loaded, which the plain row from
    # require_case_access does not have — re-fetched here rather than adding
    # selectinload to every route's dependency for the one caller that needs it.
    case = await _load_case_with_entities(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    decision = (
        await db.execute(
            select(KadiResolutionDecision).where(
                KadiResolutionDecision.id == decision_id, KadiResolutionDecision.case_id == case_id
            )
        )
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(status_code=404, detail="Resolution decision not found for this case")

    try:
        await apply_feedback(db, case, decision, body.same_entity)
    except DecisionAlreadyResolved:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This decision was already answered.")
    except DecisionStale:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The entities in this decision have changed since it was made. Refresh and try again.",
        )

    results = await recalibrate(db, decision.entity_type)
    await db.commit()

    # Entity context changed; refresh the consent-bounded module insights.
    await run_auto_triggers(db, case_id, trigger="resolution_feedback")
    await db.commit()

    return ResolutionFeedbackResponse(
        decision=_decision_response(decision),
        calibration=[
            CalibrationAttempt(
                scope=r.scope,
                status=r.status,
                merge_threshold=r.thresholds.merge,
                ask_threshold=r.thresholds.ask,
                sample_count=r.metrics.sample_count,
                reasons=r.reasons,
            )
            for r in results
        ],
    )


@router.get("/resolution/calibration")
async def resolution_calibration(db: AsyncSession = Depends(get_db)):
    """Active entity-resolution thresholds and recent recalibration attempts. Aggregate
    numbers only — no case data."""
    active: Dict[str, Any] = {}
    for scope in (ALL_TYPES_SCOPE, *sorted(RESOLVABLE_ENTITY_TYPES)):
        row = await latest_calibration(db, scope)
        if row is not None:
            active[scope] = {
                "merge": row.merge_threshold,
                "ask": row.ask_threshold,
                "calibration_id": row.id,
                "sample_count": row.sample_count,
                "metrics": row.metrics,
                "calibrated_at": row.created_at,
            }
    labeled = (
        await db.execute(
            select(func.count()).select_from(KadiResolutionDecision).where(
                KadiResolutionDecision.feedback_same_entity.is_not(None)
            )
        )
    ).scalar_one()
    recent = (
        await db.execute(
            select(KadiThresholdCalibration).order_by(KadiThresholdCalibration.created_at.desc()).limit(10)
        )
    ).scalars().all()
    return {
        "method": (
            "Deterministic, bounded recalibration of the merge and ask thresholds from user "
            "confirm/reject answers. Not RLHF: there is no reward model and no policy optimization."
        ),
        "defaults": ResolutionThresholds().model_dump(),
        "active": active,
        "labeled_decisions": labeled,
        "recent_attempts": [
            {
                "scope": r.scope,
                "status": r.status,
                "merge_threshold": r.merge_threshold,
                "ask_threshold": r.ask_threshold,
                "sample_count": r.sample_count,
                "reasons": r.reasons,
                "created_at": r.created_at,
            }
            for r in recent
        ],
    }
