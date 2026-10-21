"""Case knowledge graph (#86) and auto-triggered module insights (#32)."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auto_triggers import readiness_for_case
from app.case_auth import require_case_access
from app.consent import require_case_consent
from app.database import get_db
from app.models import (
    KadiCase,
    KadiModuleInsight,
    KadiResolutionDecision,
)
from kadi.graph import CaseGraph, EntityRecord, PendingLink, StayInfo, build_case_graph
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
from app.api.v1.endpoints.kadi.loaders import _load_case_with_entities

logger = logging.getLogger("arogyarakshak.api.kadi")
router = APIRouter()


# --- Case knowledge graph (#86) -----------------------------------------------

@router.get("/cases/{case_id}/graph", response_model=CaseGraph)
async def case_graph(
    case_id: str,
    _case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Typed node-link graph of this case's entities. Every edge carries its evidence.

    Not consent-gated, for the same reason as GET /cases/{case_id}: it is Kadi's own view
    of the case, not another module's. Still access-gated (app.case_auth)."""
    case = await _load_case_with_entities(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    pending = (
        await db.execute(
            select(KadiResolutionDecision).where(
                KadiResolutionDecision.case_id == case_id,
                KadiResolutionDecision.status == "pending",
                KadiResolutionDecision.mention_entity_id.is_not(None),
            )
        )
    ).scalars().all()
    return build_case_graph(
        StayInfo(
            case_id=case_id,
            admission_date=case.date_admission.date().isoformat() if case.date_admission else None,
            discharge_date=case.date_discharge.date().isoformat() if case.date_discharge else None,
        ),
        [
            EntityRecord(id=e.id, name=e.name or "", type=e.type, value=e.value, meta=e.meta if isinstance(e.meta, dict) else {})
            for e in case.entities
        ],
        [
            PendingLink(
                decision_id=d.id,
                mention_entity_id=d.mention_entity_id,
                candidate_entity_id=d.candidate_entity_id,
                confidence=d.confidence,
            )
            for d in pending
        ],
    )


# --- Auto-triggered module insights (#32) -------------------------------------

@router.get("/cases/{case_id}/insights")
async def case_insights(
    case_id: str,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Readiness of every module check for this case, and the latest result of each check
    Kadi ran automatically. Consent-gated: these are other modules' analyses of the case."""
    case = require_case_consent(case)
    readiness = await readiness_for_case(db, case)
    rows = (
        await db.execute(select(KadiModuleInsight).where(KadiModuleInsight.case_id == case_id))
    ).scalars().all()
    return {
        "case_id": case_id,
        "readiness": [r.model_dump() for r in readiness],
        "insights": [
            {
                "module_check": r.module_check,
                "status": r.status,
                "trigger": r.trigger,
                "summary": r.summary,
                "missing_context": r.missing_context or [],
                "error_id": r.error_id,
                "updated_at": r.updated_at,
            }
            for r in rows
        ],
    }
