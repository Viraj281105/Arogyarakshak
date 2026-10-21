"""
BillNyay API Endpoints.

Hospital bill auditing, appeal drafting (5-agent pipeline), appeal PDF download/verify and
grievance package generation. Handlers authorise, enforce consent and translate errors;
the work lives in ``app.services.billnyay_audit`` (CGHS audit),
``app.services.billnyay_appeal`` (appeal/grievance orchestration) and
``app.services.billnyay_llm`` (LLM client + offline fallback).
"""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.case_auth import require_case_access
from app.clinical.context import assess_case_plausibility
from app.clinical.service import current_statements_for_case, list_case_reviews
from app.config import settings
from app.consent import require_case_consent
from app.database import get_db
from app.models import BillNyayAppeal, KadiCase
from app.services import billnyay_appeal as appeal_service
from app.services.billnyay_appeal import (  # noqa: F401 — re-exported for existing importers
    UNSPECIFIED_FIELD,
    AppealResponse,
    GrievanceResponse,
    refresh_appeal_annex,
)
from app.services.billnyay_audit import (  # noqa: F401 — re-exported for existing importers
    CGHS_RATES,
    CGHS_VERSION,
    AuditResponse,
    AuditResultItem,
    _billing_unit_of,
    _load_cghs_rates,
    _match_cghs_key,
    _match_cghs_rate,
    _rate_of,
    audit_billing_lines,
    build_case_audit,
    build_case_icd_audit,
)
from app.services.billnyay_llm import GroqClient, GroqClientFallback  # noqa: F401 — re-exported
from billnyay.agents.icd_audit import ICDProcedureAuditItem
from billnyay.outcome import OutcomeEstimate, OutcomeQuery, estimate_outcome, load_registered_dataset
from billnyay.tools.bima_bharosa_crawler import RegistrationStatusResult, check_registration_status_mock
from billnyay.tools.pdf_integrity import compute_sha256, verify_signature

logger = logging.getLogger("arogyarakshak.api.billnyay")
router = APIRouter()


async def _appeal_or_409(db: AsyncSession, case_id: str) -> BillNyayAppeal:
    record = await appeal_service.load_appeal(db, case_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No appeal has been drafted for this case yet. "
                f"POST /api/v1/billnyay/cases/{case_id}/appeal first."
            ),
        )
    return record


@router.post("/cases/{case_id}/audit", response_model=AuditResponse)
async def audit_bill(
    case_id: str,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Audits hospital bill items against CGHS rate schedules."""
    require_case_consent(case)
    return await build_case_audit(case_id, db)


@router.post("/cases/{case_id}/appeal", response_model=AppealResponse)
async def draft_appeal(
    case_id: str,
    language: str = Query("en", description="Appeal letter language: en, hi, or mr (#39)."),
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Runs the 5-agent pipeline to generate an IRDAI-compliant appeal letter."""
    if language not in ("en", "hi", "mr"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unsupported language '{language}'. Use en, hi, or mr.",
        )
    require_case_consent(case)
    try:
        return await appeal_service.draft_case_appeal(db, case_id, language)
    except appeal_service.AppealDraftingFailed:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Appeal drafting failed: the drafting agent returned no letter.",
        )


@router.get("/cases/{case_id}/clinical-plausibility")
async def clinical_plausibility(
    case_id: str,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Bounded plausibility check between the documented diagnosis and intervention
    (ADR-011). Not a medical-necessity determination and not an outcome prediction; when
    it cannot decide, it says so and recommends a named human reviewer."""
    require_case_consent(case)
    assessment, safety = await assess_case_plausibility(db, case_id)
    reviews = [r for r in await list_case_reviews(db, case_id) if r.source_module == "billnyay"]
    statements = await current_statements_for_case(db, case_id, ["billnyay"])
    return {
        "case_id": case_id,
        "assessment": assessment.model_dump(),
        "safety_escalations": safety["escalations"],
        # EVALUATED or UNAVAILABLE — an unavailable check is never "no escalation".
        "safety_check": {"status": safety.get("status", "EVALUATED"), "note": safety.get("coverage_note")},
        "clinical_review": {
            "required": assessment.clinical_review_required,
            "status": "CLINICAL_REVIEW_REQUIRED" if assessment.clinical_review_required else "NOT_REQUIRED",
            "open_or_completed_reviews": [
                {"review_id": r.id, "status": r.status} for r in reviews if r.status != "CANCELLED"
            ],
            "human_statement_exists": bool(statements),
        },
    }


@router.get("/cases/{case_id}/appeal/pdf")
async def download_appeal_pdf(
    case_id: str,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Downloads the exact signed PDF generated by the most recent POST .../appeal
    for this case (#66). Renders strictly from the stored bytes — never regenerated
    on the fly — so what is downloaded always matches what was hashed and signed."""
    require_case_consent(case)
    record = await _appeal_or_409(db, case_id)
    return Response(
        content=record.pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=appeal_{case_id}.pdf"},
    )


@router.get("/cases/{case_id}/appeal/verify")
async def verify_appeal_pdf(
    case_id: str,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Verifies the stored appeal PDF's integrity (#66): recomputes its SHA-256 and
    checks the stored HMAC signature. This proves the stored bytes were not altered
    since ArogyaRakshak generated and signed them — it is NOT a licensed digital
    signature certificate (DSC) under the IT Act, 2000; see
    billnyay.tools.pdf_integrity for what this can and cannot vouch for.
    """
    require_case_consent(case)
    record = await _appeal_or_409(db, case_id)
    return {
        "case_id": case_id,
        "sha256_hash": record.sha256_hash,
        "hash_matches_stored_bytes": compute_sha256(record.pdf_bytes) == record.sha256_hash,
        "signature_valid": verify_signature(record.pdf_bytes, record.hmac_signature, settings.document_signing_secret),
        "note": (
            "This confirms the stored PDF is byte-for-byte what ArogyaRakshak generated "
            "and signed. It is not a licensed digital signature certificate (DSC) under "
            "the IT Act, 2000."
        ),
    }


@router.get("/cases/{case_id}/icd-audit", response_model=ICDProcedureAuditItem)
async def audit_icd_procedure(
    case_id: str,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Flags whether the billed procedure(s) look clinically consistent with the
    diagnosis's ICD-10 code (#64), using a curated reference subset — see
    billnyay.agents.icd_audit for its coverage and honesty caveats."""
    require_case_consent(case)
    return await build_case_icd_audit(case_id, db)


class OutcomeEstimateRequest(BaseModel):
    dispute_category: str = Field(..., min_length=1, max_length=64, json_schema_extra={"example": "PED_NON_DISCLOSURE"})
    forum: Literal["insurer_grievance", "insurance_ombudsman", "consumer_commission"] = "insurance_ombudsman"


@router.post("/outcome-estimate", response_model=OutcomeEstimate)
async def estimate_dispute_outcome(req: OutcomeEstimateRequest):
    """Historical outcome base rate for a dispute category (#90).

    Returns a probability only when a cited, non-synthetic historical dataset with enough
    decided disputes is registered (billnyay/data/dispute_outcomes). None exists today, so
    the status is INSUFFICIENT_EVIDENCE. Request-body only; reads no case context.
    """
    return estimate_outcome(
        OutcomeQuery(dispute_category=req.dispute_category, forum=req.forum),
        load_registered_dataset(),
    )


@router.get("/grievance/registration-status", response_model=RegistrationStatusResult)
async def grievance_registration_status(
    complaint_reference: str = Query(..., description="Bima Bharosa complaint reference number")
):
    """Mock Bima Bharosa portal registration-status check (#67). See
    billnyay.tools.bima_bharosa_crawler for why this is deliberately mock-only —
    ArogyaRakshak is not authorized to automate interactions with the live portal."""
    return check_registration_status_mock(complaint_reference)


@router.post("/cases/{case_id}/grievance", response_model=GrievanceResponse)
async def draft_grievance(
    case_id: str,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Auto-drafts an IRDAI Bima Bharosa portal complaint package (#51).

    Reuses the Auditor Agent extraction the appeal runs, so the complaint reflects this
    case's actual denial code/reason/procedure — or honestly reports them as not
    extracted, via `denial_facts_extracted` (no case-independent templating).
    """
    case = require_case_consent(case)
    return await appeal_service.draft_case_grievance(db, case)
