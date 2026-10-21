"""Claim Pack endpoint (ADR-015): one ZIP for the person helping the patient.

Extends the DaaviSetu claim package (#81) across modules. Read-only and in-memory: it
gathers what is already stored for the case (plus deterministic, local computations over
the stored entities) and never calls an LLM, the network, or writes a row. Original
uploaded documents are not retained anywhere, so they cannot be in the pack.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import daavisetu_playbooks as playbooks
from app.case_auth import require_case_access
from app.claim_pack import ClaimPackInput, build_claim_pack_zip
from app.clinical import service as clinical_service
from app.clinical.context import load_entity_records
from app.consent import require_case_consent
from app.database import get_db
from app.models import (
    BillNyayAppeal,
    BimaNyayGrievance,
    BimaNyayTimelineEvent,
    DaaviSetuClaim,
    KadiCase,
    KadiEntity,
)
from app.services.billnyay_audit import build_case_audit
from app.services.daavisetu_claims import claim_data_from_record
from app.services.dawacheck_benchmarks import build_case_medicine_benchmarks
from daavisetu.generator import generate_preauth_pdf
from daavisetu.readiness import render_readiness_text

logger = logging.getLogger("arogyarakshak.api.claim_pack")
router = APIRouter()


@router.get("/cases/{case_id}/claim-pack")
async def download_claim_pack(
    case_id: str,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Downloads the case's Claim Pack ZIP: cover sheet, documentation checklist, BimaNyay
    deadline timeline, BillNyay audit and appeal draft (only if they exist), DawaCheck rows
    and a manifest of exactly what is and is not included.

    Requires the per-case access token (ADR-009) and cross-module consent (ADR-007/011).
    An empty case still returns a pack whose sections say "not available for this case".
    """
    require_case_consent(case)

    # 1. Documentation checklist (generic baseline; ADR-011 reviewer decisions only).
    readiness = playbooks.build_report(
        await load_entity_records(db, case_id),
        case.total_charged,
        await clinical_service.latest_fact_decisions(db, case_id),
        None,
    )
    readiness_summary = {
        "present": readiness.present_count,
        "missing": readiness.missing_count,
        "needs_clinical_confirmation": readiness.needs_clinical_confirmation_count,
        "reviewer_decisions": sum(
            1 for i in readiness.items if i.clinical_decision and i.clinical_decision.decision != "PENDING"
        ),
    }

    # 2. BimaNyay grievances (and their stored milestone dates) linked to this case.
    grievances = []
    grievance_rows = (
        await db.execute(
            select(BimaNyayGrievance)
            .where(BimaNyayGrievance.case_id == case_id)
            .order_by(BimaNyayGrievance.created_at)
        )
    ).scalars().all()
    for g in grievance_rows:
        events = (
            await db.execute(
                select(BimaNyayTimelineEvent)
                .where(BimaNyayTimelineEvent.grievance_id == g.id)
                .order_by(BimaNyayTimelineEvent.deadline_date)
            )
        ).scalars().all()
        grievances.append(
            {
                "insurer_name": g.insurer_name,
                "claim_number": g.claim_number,
                "date_initiated": g.date_initiated,
                "current_tier": g.current_tier,
                "events": [
                    {
                        "tier": e.tier,
                        "title": e.title,
                        "deadline_date": e.deadline_date,
                        "status": e.status,
                        "instructions": e.instructions,
                    }
                    for e in events
                ],
            }
        )

    # 3. BillNyay audit: deterministic CGHS comparison over stored billing lines (no LLM).
    has_billing = (
        await db.execute(
            select(KadiEntity.id)
            .join(KadiCase.entities)
            .where(KadiCase.id == case_id, KadiEntity.type == "billing_item")
            .limit(1)
        )
    ).first() is not None
    audit = (await build_case_audit(case_id, db)).model_dump() if has_billing else None

    # 4. Appeal draft only if one was already generated and stored.
    appeal_letter = (
        await db.execute(select(BillNyayAppeal.appeal_letter).where(BillNyayAppeal.case_id == case_id))
    ).scalar_one_or_none()

    # 5. DawaCheck rows (deterministic). The helper stages learned brand mappings on the
    # session; this read-only route discards them rather than committing.
    medicines = [m.model_dump(mode="json") for m in await build_case_medicine_benchmarks(case_id, db)]
    await db.rollback()

    # 6. The pre-auth form, only if the person already submitted claim details.
    claim = (
        await db.execute(select(DaaviSetuClaim).where(DaaviSetuClaim.case_id == case_id))
    ).scalar_one_or_none()
    preauth_pdf = (
        generate_preauth_pdf(claim_id=claim.id, claim_input=claim_data_from_record(claim)) if claim else None
    )

    zip_bytes = build_claim_pack_zip(
        ClaimPackInput(
            case_id=case_id,
            generated_at=datetime.now(),
            readiness_text=render_readiness_text(readiness),
            readiness_summary=readiness_summary,
            grievances=grievances,
            audit=audit,
            appeal_letter=appeal_letter,
            medicines=medicines,
            preauth_pdf=preauth_pdf,
            claim_id=claim.id if claim else None,
        )
    )
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=claim_pack_{case_id}.zip"},
    )
