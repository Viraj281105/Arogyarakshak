"""
BimaNyay API Endpoints.

Handles health insurance denial audits, statutory clause analysis,
and multi-tier IRDAI grievance timeline tracking.
"""

import hmac
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.case_auth import CASE_ACCESS_TOKEN_HEADER, hash_case_access_token, require_case_access
from app.clinical.serializers import annex_dict, statement_view
from app.clinical.service import current_statements_for_case, list_case_reviews
from app.consent import require_case_consent
from app.database import get_db
from app.models import BimaNyayCase, BimaNyayGrievance, BimaNyayTimelineEvent, KadiCase
from kadi.clinical_review.annex import NO_HUMAN_STATEMENT_NOTICE, render_annex
from bimanyay import (
    ClaimDenialInput,
    DisputeAuditResult,
    GrievanceTrackerResponse,
    analyze_insurance_denial,
    calculate_grievance_timeline,
)

logger = logging.getLogger("arogyarakshak.api.bimanyay")
router = APIRouter()


async def _authorize_optional_case(
    case_id: Optional[str],
    x_case_access_token: Optional[str],
    db: AsyncSession,
) -> Optional[KadiCase]:
    """SEC-04: BimaNyay previously created dispute records with no case linkage at all —
    unauthorized, unauthenticated, and outside the case-deletion cascade (ADR-009/#66
    docstring: "BimaNyay's dispute records are a separate, not-yet-linked data domain").

    `case_id` stays optional (BimaNyay's own screen has no case-creation flow — see
    module docstring), preserving stand-alone use. But when a caller DOES supply one, it
    must be authorized exactly like every other case-scoped route: the case must exist,
    the caller must present its real access token (never merely knowing the id), and the
    case must have opted into cross-module consent — this record becomes part of that
    case's shared context and must be deleted when the case is.
    """
    if not case_id:
        return None

    result = await db.execute(select(KadiCase).where(KadiCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    stored_hash = case.access_token_hash or ""
    presented_hash = hash_case_access_token(x_case_access_token or "")
    if not x_case_access_token or not stored_hash or not hmac.compare_digest(presented_hash, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The provided case access token is invalid for this case.",
        )

    return require_case_consent(case)


class TimelineRequest(BaseModel):
    insurer_name: str = Field(..., description="Insurance company name")
    date_initiated: str = Field(..., description="Date grievance initiated (YYYY-MM-DD)")
    claim_number: Optional[str] = Field(None, description="Insurance claim reference number")
    current_tier: str = Field(default="LEVEL_1_GRO", description="Current escalation tier")


@router.post("/analyze", response_model=DisputeAuditResult, status_code=status.HTTP_200_OK)
async def analyze_denial(
    req: ClaimDenialInput,
    language: str = "en",
    case_id: Optional[str] = Query(
        None, description="Optional: link this dispute record to an existing Kadi case (SEC-04)."
    ),
    x_case_access_token: Optional[str] = Header(None, alias=CASE_ACCESS_TOKEN_HEADER),
    db: AsyncSession = Depends(get_db)
):
    """
    Audits an insurance claim repudiation or deduction against IRDAI regulations.
    Generates 3-tier appeal documents: GRO, IRDAI Bima Bharosa, and Ombudsman in English, Hindi, or Marathi.
    """
    linked_case = await _authorize_optional_case(case_id, x_case_access_token, db)
    try:
        result = analyze_insurance_denial(req, language=language)

        # Persist audit record in database
        record_id = str(uuid.uuid4())
        case_record = BimaNyayCase(
            id=record_id,
            case_id=linked_case.id if linked_case else None,
            policy_number=req.policy_number,
            insurer_name=req.insurer_name,
            policy_age_years=req.policy_age_years,
            claimed_amount=req.claimed_amount,
            denied_amount=req.denied_or_deducted_amount,
            denial_category=req.denial_category,
            denial_reason_raw=req.denial_reason_raw,
            diagnosis=req.diagnosis,
            is_wrongful=result.is_wrongful_denial,
            reversal_probability=result.reversal_probability_score,
            primary_grounds=result.primary_dispute_grounds,
        )
        db.add(case_record)
        await db.commit()

        return result
    except Exception:
        # Re-raised so the application-wide handler returns a safe payload with a
        # correlation id. Returning str(e) here leaked internal detail to the client.
        logger.exception("Error analyzing claim denial for policy %s", req.policy_number)
        raise


@router.post("/timeline", response_model=GrievanceTrackerResponse, status_code=status.HTTP_200_OK)
async def track_timeline(
    req: TimelineRequest,
    case_id: Optional[str] = Query(
        None, description="Optional: link this grievance record to an existing Kadi case (SEC-04)."
    ),
    x_case_access_token: Optional[str] = Header(None, alias=CASE_ACCESS_TOKEN_HEADER),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculates statutory milestone deadlines and SLA tracking for dispute escalation.
    """
    linked_case = await _authorize_optional_case(case_id, x_case_access_token, db)
    try:
        timeline = calculate_grievance_timeline(
            insurer_name=req.insurer_name,
            date_initiated=req.date_initiated,
            claim_number=req.claim_number,
            current_tier=req.current_tier,
        )

        # Persist grievance record
        grievance_id = str(uuid.uuid4())
        grievance_record = BimaNyayGrievance(
            id=grievance_id,
            case_id=linked_case.id if linked_case else None,
            claim_number=req.claim_number,
            insurer_name=req.insurer_name,
            current_tier=req.current_tier,
            date_initiated=req.date_initiated,
        )
        db.add(grievance_record)

        for event in timeline.timeline_events:
            event_record = BimaNyayTimelineEvent(
                id=str(uuid.uuid4()),
                grievance_id=grievance_id,
                tier=event.tier,
                title=event.title,
                deadline_date=event.deadline_date,
                status=event.status,
                instructions=event.instructions,
            )
            db.add(event_record)

        await db.commit()
        return timeline
    except Exception:
        logger.exception("Error tracking grievance timeline for insurer %s", req.insurer_name)
        raise


@router.get("/cases/{case_id}/clinical-statements")
async def clinical_statements_for_appeal(
    case_id: str,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Finalized, attributed clinician statements for this case's BimaNyay appeal (ADR-011),
    plus the verbatim annex to append to the GRO / Bima Bharosa / Ombudsman drafts. When
    none exists the annex says so — the drafts must never imply a clinician's opinion."""
    require_case_consent(case)
    statements = await current_statements_for_case(db, case_id, ["bimanyay"])
    reviews = [r for r in await list_case_reviews(db, case_id) if r.source_module == "bimanyay"]
    return {
        "case_id": case_id,
        "human_clinical_statement_attached": bool(statements),
        "statements": [statement_view(s) for s in statements],
        "reviews": [{"review_id": r.id, "status": r.status} for r in reviews],
        # Appended to insurer-facing drafts only when a statement exists.
        "annex_text": render_annex([annex_dict(s) for s in statements]) if statements else "",
        # Patient-facing only; never paste this into a filing.
        "clinical_statement_notice": "" if statements else NO_HUMAN_STATEMENT_NOTICE,
    }
