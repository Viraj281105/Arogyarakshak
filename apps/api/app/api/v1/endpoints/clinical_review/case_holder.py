"""Case-holder routes (X-Case-Access-Token): request, assign, cancel and read clinical
reviews of a case, its audit trail and clinical context."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kadi.clinical_review import (
    PROVENANCE_DESCRIPTIONS,
    ProvenanceClass,
    ReviewTrigger,
    ReviewType,
    SourceModule,
)
from kadi.clinical_review.evidence import SupplementaryItem

from app.case_auth import require_case_access
from app.clinical import service
from app.clinical.audit import events_for_review
from app.clinical.context import (
    assess_case_plausibility,
    evaluate_case_safety,
    evaluate_case_safety_or_unavailable,
    load_entity_records,
)
from app.clinical.serializers import (
    case_holder_review_view,
)
from app.clinical.transcription_service import case_task_view, list_case_tasks
from app.database import get_db
from app.models import BimaNyayCase, KadiCase, KadiClinicalReviewer

router = APIRouter()
from app.api.v1.endpoints.clinical_review.schemas import AssignRequest, ReviewCreate


DEFAULT_QUESTIONS = {
    SourceModule.BILLNYAY.value: (
        "Based on the evidence provided, what is your professional opinion on whether the "
        "documented diagnosis and the billed intervention are clinically consistent? State what "
        "the records do and do not show, and the limits of your review."
    ),
    SourceModule.BIMANYAY.value: (
        "Based on the records you review, what is your professional opinion on the insurer's "
        "stated reason for denial? State what the records do and do not show, and the limits of "
        "your review."
    ),
}
GENERIC_QUESTION = (
    "Based on the evidence provided, please give your professional opinion on the question the "
    "patient needs answered, stating what the records do and do not show."
)


# --- Case-holder routes -----------------------------------------------------------

async def _supplementary(db: AsyncSession, case: KadiCase, source_module: str, trigger: str, entities) -> List[SupplementaryItem]:
    items: List[SupplementaryItem] = []
    if source_module == SourceModule.BILLNYAY.value:
        assessment, _ = await assess_case_plausibility(db, case.id, entities)
        items.append(SupplementaryItem(
            item_id="SUPP-plausibility",
            kind="machine_finding",
            label="BillNyay clinical plausibility check (machine-derived)",
            value=f"{assessment.status}: {assessment.summary} {assessment.disclaimer}",
            provenance=ProvenanceClass.AI_DERIVED,
            source=assessment.method,
        ))
    if source_module == SourceModule.BIMANYAY.value:
        row = await db.execute(
            select(BimaNyayCase).where(BimaNyayCase.case_id == case.id).order_by(BimaNyayCase.created_at.desc())
        )
        denial = row.scalars().first()
        if denial:
            items.append(SupplementaryItem(
                item_id="SUPP-denial",
                kind="denial_record",
                label="Insurer's stated denial reason (entered by the case holder)",
                value=f"Category: {denial.denial_category}. Reason: {denial.denial_reason_raw}. Insurer: {denial.insurer_name}.",
                provenance=ProvenanceClass.PATIENT_PROVIDED,
                source="BimaNyay denial analysis input",
            ))
    if trigger == ReviewTrigger.SAFETY_RULE.value:
        safety = await evaluate_case_safety(db, case.id, entities)
        for i, esc in enumerate(safety["escalations"][:5]):
            items.append(SupplementaryItem(
                item_id=f"SUPP-safety-{i}",
                kind="safety_escalation",
                label=f"Safety rule fired: {esc['title']} (v{esc['rule_version']})",
                value=f"Matched terms: {', '.join(esc['matched_terms'])}. Source: {esc['source']['name']}.",
                provenance=ProvenanceClass.AI_DERIVED,
                source="ArogyaRakshak clinical safety rule (keyword trigger)",
            ))
    return items


async def _case_view(db: AsyncSession, review) -> Dict[str, Any]:
    reviewer = await db.get(KadiClinicalReviewer, review.assigned_reviewer_id) if review.assigned_reviewer_id else None
    return case_holder_review_view(
        review, reviewer, await service.statements_for_review(db, review.id), await service.facts_for_review(db, review.id)
    )


@router.post("/cases/{case_id}/clinical-reviews", status_code=status.HTTP_201_CREATED)
async def request_clinical_review(
    case_id: str,
    req: ReviewCreate,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Requests an attributable statement from a named human reviewer. The evidence packet
    is frozen now from the chosen evidence types; nothing else from the case is shared."""
    entities = await load_entity_records(db, case_id)
    question = req.clinical_question or DEFAULT_QUESTIONS.get(req.source_module.value, GENERIC_QUESTION)
    review = await service.create_review(
        db,
        case,
        source_module=req.source_module.value,
        review_type=ReviewType.CLINICAL_STATEMENT.value,
        clinical_question=question,
        entities=entities,
        evidence_scope=req.evidence_scope,
        insurer_name=req.insurer_name,
        trigger=req.trigger.value,
        trigger_ref=req.trigger_ref,
        share_with_reviewer_consent=req.share_with_reviewer_consent,
        supplementary=await _supplementary(db, case, req.source_module.value, req.trigger.value, entities),
    )
    await db.commit()
    return await _case_view(db, review)


@router.get("/cases/{case_id}/clinical-reviews")
async def list_clinical_reviews(
    case_id: str,
    source_module: Optional[SourceModule] = None,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    reviews = await service.list_case_reviews(db, case_id)
    if source_module:
        reviews = [r for r in reviews if r.source_module == source_module.value]
    return [await _case_view(db, r) for r in reviews]


@router.get("/cases/{case_id}/clinical-reviews/{review_id}")
async def get_clinical_review(
    case_id: str, review_id: str, case: KadiCase = Depends(require_case_access), db: AsyncSession = Depends(get_db)
):
    return await _case_view(db, await service.get_case_review(db, case_id, review_id))


@router.post("/cases/{case_id}/clinical-reviews/{review_id}/assign")
async def assign_clinical_review(
    case_id: str,
    review_id: str,
    req: AssignRequest,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    review = await service.get_case_review(db, case_id, review_id)
    await service.assign_review(db, case, review, req.reviewer_id)
    await db.commit()
    return await _case_view(db, review)


@router.post("/cases/{case_id}/clinical-reviews/{review_id}/cancel")
async def cancel_clinical_review(
    case_id: str, review_id: str, case: KadiCase = Depends(require_case_access), db: AsyncSession = Depends(get_db)
):
    """Withdraws the patient's sharing for this review: the reviewer loses access
    immediately and no package will present its statement as current."""
    review = await service.get_case_review(db, case_id, review_id)
    await service.cancel_review(db, case, review)
    await db.commit()
    return await _case_view(db, review)


@router.get("/cases/{case_id}/clinical-reviews/{review_id}/audit")
async def case_review_audit(
    case_id: str, review_id: str, case: KadiCase = Depends(require_case_access), db: AsyncSession = Depends(get_db)
):
    review = await service.get_case_review(db, case_id, review_id)
    return await events_for_review(db, review.id)


@router.get("/cases/{case_id}/clinical-context")
async def clinical_context(case_id: str, case: KadiCase = Depends(require_case_access), db: AsyncSession = Depends(get_db)):
    """Every human-review output for the case, each labelled with its provenance class, next
    to the machine-derived safety signals. Human judgment and AI analysis never merge."""
    reviews = [await _case_view(db, r) for r in await service.list_case_reviews(db, case_id)]
    tasks = [await case_task_view(db, t) for t in await list_case_tasks(db, case_id)]
    return {
        "case_id": case_id,
        "reviews": reviews,
        "human_statements": [
            r["current_statement"] for r in reviews if r["current_statement"] and r["status"] != "CANCELLED"
        ],
        "fact_decisions": [f for r in reviews if r["status"] != "CANCELLED" for f in r["facts"] if f["decision"] != "PENDING"],
        "transcriptions": tasks,
        "safety": await evaluate_case_safety_or_unavailable(db, case_id),
        "provenance_legend": {p.value: PROVENANCE_DESCRIPTIONS[p] for p in ProvenanceClass},
    }
