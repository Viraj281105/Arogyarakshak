"""
Kadi — Clinical Review endpoints (ADR-011). Mounted under /api/v1/kadi.

Three audiences, three credentials:
- case holder: X-Case-Access-Token, routes under /cases/{case_id}/...
- reviewer:    X-Reviewer-Token,   routes under /clinical-reviews/... and /clinical-reviewers/me
- operator:    X-Governance-Admin-Key, board seating / verification attempts only.

AI never holds a reviewer credential, so no model output can create, finalize or sign a
statement: every write that carries professional attribution requires one.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kadi.clinical_review import (
    PROVENANCE_DESCRIPTIONS,
    ActorType,
    AuditEventType,
    ProvenanceClass,
    ReviewerCategory,
    ReviewTrigger,
    ReviewType,
    SourceModule,
    VerificationStatus,
)
from kadi.clinical_review.evidence import SupplementaryItem
from kadi.clinical_review.lifecycle import (
    FACT_DECISION_CONFIRMATION_TEXT,
    FINALIZATION_CONFIRMATION_TEXT,
)
from kadi.clinical_review.verification import (
    DEMO_VERIFICATION_SOURCE,
    UnavailableRegistryAdapter,
    initial_verification_status,
)

from app.case_auth import require_case_access
from app.clinical import service
from app.clinical.audit import events_for_review, record_event
from app.clinical.auth import (
    generate_credential,
    listed_in_directory,
    require_governance_admin,
    require_reviewer,
    reviewer_available,
)
from app.clinical.context import assess_case_plausibility, evaluate_case_safety, load_entity_records
from app.clinical.serializers import (
    case_holder_review_view,
    fact_view,
    review_summary,
    reviewer_public,
    statement_view,
)
from app.clinical.transcription_service import case_task_view, list_case_tasks
from app.config import settings
from app.database import get_db
from app.models import BimaNyayCase, KadiCase, KadiClinicalReviewer

router = APIRouter()

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


# --- Schemas ------------------------------------------------------------------

class ReviewerRegistration(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    category: ReviewerCategory
    designation: Optional[str] = Field(None, max_length=120)
    specialty: Optional[str] = Field(None, max_length=120)
    registration_number: Optional[str] = Field(None, max_length=60)
    registration_authority: Optional[str] = Field(None, max_length=160)
    affiliation: Optional[str] = Field(None, max_length=200)
    standing_disclosures: Optional[str] = Field(None, max_length=1000)
    reviewer_notes: Optional[str] = Field(None, max_length=1000)


class ReviewCreate(BaseModel):
    source_module: SourceModule
    clinical_question: Optional[str] = Field(None, max_length=1000)
    evidence_scope: Optional[List[str]] = None
    insurer_name: Optional[str] = Field(None, max_length=120)
    trigger: ReviewTrigger = ReviewTrigger.MANUAL
    trigger_ref: Optional[str] = Field(None, max_length=80)
    share_with_reviewer_consent: bool = False


class AssignRequest(BaseModel):
    reviewer_id: str = Field(..., max_length=40)


class AcceptRequest(BaseModel):
    coi_category: str
    coi_disclosure: Optional[str] = Field(None, max_length=1000)


class DeclineRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class StatementWrite(BaseModel):
    evidence_reviewed: List[str] = Field(..., max_length=60)
    reviewer_statement: str = Field(..., max_length=8000)
    limitations: str = Field(..., max_length=3000)


class ConfirmRequest(BaseModel):
    confirmation: bool = False
    confirmation_text: Optional[str] = Field(None, max_length=300)


class WithdrawRequest(BaseModel):
    reason: str = Field(..., max_length=500)


class FactDecisionRequest(ConfirmRequest):
    decision: Literal["CONFIRMED", "REJECTED", "CANNOT_DETERMINE"]
    note: Optional[str] = Field(None, max_length=1000)


class BoardSeatRequest(BaseModel):
    seated: bool


class VerificationRequest(BaseModel):
    mode: Literal["external", "demo"]


# --- Reviewer registry ------------------------------------------------------------

@router.post("/clinical-reviewers", status_code=status.HTTP_201_CREATED)
async def register_reviewer(req: ReviewerRegistration, db: AsyncSession = Depends(get_db)):
    """Self-registration. The credential is returned exactly once. Verification status can
    never exceed SELF_DECLARED here — a claimed registration number is shown as claimed."""
    token, token_hash = generate_credential()
    reviewer = KadiClinicalReviewer(
        id=f"REV-{uuid.uuid4().hex[:12]}",
        name=req.name.strip(),
        category=req.category.value,
        designation=req.designation,
        specialty=req.specialty,
        registration_number=(req.registration_number or "").strip() or None,
        registration_authority=req.registration_authority,
        verification_status=initial_verification_status(req.registration_number),
        affiliation=req.affiliation,
        standing_disclosures=req.standing_disclosures,
        reviewer_notes=req.reviewer_notes,
        credential_hash=token_hash,
    )
    db.add(reviewer)
    record_event(
        db,
        event_type=AuditEventType.REVIEWER_REGISTERED.value,
        subject_type="REVIEWER",
        subject_id=reviewer.id,
        actor_type=ActorType.REVIEWER.value,
        actor_id=reviewer.id,
        details={"category": reviewer.category, "verification_status": reviewer.verification_status},
    )
    await db.commit()
    return {
        "reviewer": reviewer_public(reviewer),
        "reviewer_token": token,
        "note": (
            "Store this reviewer credential now — it is shown only once. Send it as the "
            "X-Reviewer-Token header. Your registration details are shown to patients as "
            "self-declared until verified."
        ),
    }


@router.get("/clinical-reviewers")
async def reviewer_directory(
    category: Optional[ReviewerCategory] = None,
    specialty: Optional[str] = Query(None, max_length=120),
    db: AsyncSession = Depends(get_db),
):
    """Public directory of reviewers a patient may pick without knowing them already.

    Only independently verified reviewers are listed (plus demo fixtures in demo mode).
    Self-registration cannot be verified in this build, so self-declared reviewers are
    never listed — otherwise anyone could list themselves under a real doctor's name.
    A patient assigns their own doctor by the reviewer ID that doctor gives them."""
    query = select(KadiClinicalReviewer).where(KadiClinicalReviewer.is_active.is_(True))
    if category:
        query = query.where(KadiClinicalReviewer.category == category.value)
    rows = [r for r in (await db.execute(query.order_by(KadiClinicalReviewer.name))).scalars().all() if listed_in_directory(r)]
    if specialty:
        rows = [r for r in rows if r.specialty and specialty.lower() in r.specialty.lower()]
    return [reviewer_public(r) for r in rows[:200]]


@router.get("/clinical-reviewers/me")
async def reviewer_me(reviewer: KadiClinicalReviewer = Depends(require_reviewer)):
    return reviewer_public(reviewer)


@router.post("/clinical-reviewers/me/deactivate")
async def deactivate_me(reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)):
    reviewer.is_active = False
    record_event(db, event_type=AuditEventType.REVIEWER_DEACTIVATED.value, subject_type="REVIEWER",
                 subject_id=reviewer.id, actor_type=ActorType.REVIEWER.value, actor_id=reviewer.id)
    await db.commit()
    return {"reviewer_id": reviewer.id, "is_active": False}


@router.get("/clinical-reviewers/{reviewer_id}")
async def reviewer_profile(reviewer_id: str, db: AsyncSession = Depends(get_db)):
    """Look up a reviewer by the ID they shared, to confirm who it is before assigning."""
    reviewer = await db.get(KadiClinicalReviewer, reviewer_id)
    if not reviewer_available(reviewer):
        raise HTTPException(status_code=404, detail="Reviewer not found.")
    return reviewer_public(reviewer)


@router.post("/clinical-reviewers/{reviewer_id}/safety-board")
async def set_board_seat(
    reviewer_id: str,
    req: BoardSeatRequest,
    admin: str = Depends(require_governance_admin),
    db: AsyncSession = Depends(get_db),
):
    reviewer = await db.get(KadiClinicalReviewer, reviewer_id)
    if reviewer is None:
        raise HTTPException(status_code=404, detail="Reviewer not found.")
    if req.seated and reviewer.category != ReviewerCategory.DOCTOR.value:
        raise HTTPException(status_code=422, detail="Only reviewers registered as doctors can sit on the safety board.")
    if req.seated and reviewer.verification_status == VerificationStatus.UNVERIFIED.value:
        raise HTTPException(status_code=422, detail="A board member must at least declare a registration number.")
    reviewer.is_safety_board_member = req.seated
    record_event(db, event_type=AuditEventType.REVIEWER_BOARD_SEAT_CHANGED.value, subject_type="REVIEWER",
                 subject_id=reviewer.id, actor_type=ActorType.GOVERNANCE_ADMIN.value, details={"seated": req.seated})
    await db.commit()
    return reviewer_public(reviewer)


@router.post("/clinical-reviewers/{reviewer_id}/verification")
async def attempt_verification(
    reviewer_id: str,
    req: VerificationRequest,
    admin: str = Depends(require_governance_admin),
    db: AsyncSession = Depends(get_db),
):
    """'external' calls the registry adapter — which, in this build, honestly reports that no
    registry integration exists and changes nothing. 'demo' is allowed only in demo mode."""
    reviewer = await db.get(KadiClinicalReviewer, reviewer_id)
    if reviewer is None:
        raise HTTPException(status_code=404, detail="Reviewer not found.")
    if req.mode == "demo":
        if not settings.clinical_demo_mode:
            raise HTTPException(status_code=403, detail="Demo verification is only available when CLINICAL_DEMO_MODE is on.")
        reviewer.verification_status = VerificationStatus.DEMO_VERIFIED.value
        reviewer.verification_source = DEMO_VERIFICATION_SOURCE
        reviewer.verification_timestamp = datetime.utcnow()
        outcome = {"outcome": VerificationStatus.DEMO_VERIFIED.value, "detail": DEMO_VERIFICATION_SOURCE}
    else:
        if not reviewer.registration_number:
            raise HTTPException(status_code=422, detail="The reviewer has not declared a registration number.")
        result = UnavailableRegistryAdapter().verify(
            registration_number=reviewer.registration_number,
            registration_authority=reviewer.registration_authority,
            name=reviewer.name,
        )
        if result.changes_status:  # unreachable with the shipped adapter; kept for a real one
            reviewer.verification_status = result.outcome
            reviewer.verification_source = result.source
            reviewer.verification_timestamp = result.checked_at
        outcome = {"outcome": result.outcome, "detail": result.detail}
    record_event(db, event_type=AuditEventType.REVIEWER_VERIFICATION_ATTEMPTED.value, subject_type="REVIEWER",
                 subject_id=reviewer.id, actor_type=ActorType.GOVERNANCE_ADMIN.value,
                 details={"mode": req.mode, "outcome": outcome["outcome"]})
    await db.commit()
    return {**outcome, "reviewer": reviewer_public(reviewer)}


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
        "safety": await evaluate_case_safety(db, case_id),
        "provenance_legend": {p.value: PROVENANCE_DESCRIPTIONS[p] for p in ProvenanceClass},
    }


# --- Reviewer routes -----------------------------------------------------------

@router.get("/clinical-reviews/assigned")
async def my_assigned_reviews(reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)):
    return [
        {**review_summary(r, reviewer), "coi_context": r.coi_context}
        for r in await service.reviewer_queue(db, reviewer)
    ]


@router.get("/clinical-reviews/{review_id}")
async def reviewer_review_detail(
    review_id: str, reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)
):
    review = await service.reviewer_review(db, reviewer, review_id, need_evidence_access=False)
    own = [s for s in await service.statements_for_review(db, review.id) if s.reviewer_id == reviewer.id]
    return {
        **review_summary(review, reviewer),
        "coi_context": review.coi_context,
        "statements": [statement_view(s, include_draft_fields=True) for s in own],
        "facts": [fact_view(f) for f in await service.facts_for_review(db, review.id)],
        "finalization_confirmation_text": FINALIZATION_CONFIRMATION_TEXT,
        "fact_decision_confirmation_text": FACT_DECISION_CONFIRMATION_TEXT,
    }


@router.post("/clinical-reviews/{review_id}/accept")
async def accept_review(
    review_id: str,
    req: AcceptRequest,
    reviewer: KadiClinicalReviewer = Depends(require_reviewer),
    db: AsyncSession = Depends(get_db),
):
    review = await service.reviewer_review(db, reviewer, review_id, need_evidence_access=False)
    await service.accept_review(db, reviewer, review, req.coi_category, req.coi_disclosure)
    await db.commit()
    return review_summary(review, reviewer)


@router.post("/clinical-reviews/{review_id}/decline")
async def decline_review(
    review_id: str,
    req: DeclineRequest,
    reviewer: KadiClinicalReviewer = Depends(require_reviewer),
    db: AsyncSession = Depends(get_db),
):
    review = await service.reviewer_review(db, reviewer, review_id, need_evidence_access=False)
    await service.decline_review(db, reviewer, review, req.reason)
    await db.commit()
    return {"review_id": review.id, "status": review.status}


@router.get("/clinical-reviews/{review_id}/evidence")
async def review_evidence(
    review_id: str, reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)
):
    review = await service.reviewer_review(db, reviewer, review_id, need_evidence_access=True)
    payload = service.evidence_for_reviewer(db, reviewer, review)
    await db.commit()
    return payload


async def _reviewer_in_review(db, reviewer, review_id):
    return await service.reviewer_review(db, reviewer, review_id, need_evidence_access=True)


@router.post("/clinical-reviews/{review_id}/statements", status_code=status.HTTP_201_CREATED)
async def create_statement(
    review_id: str,
    req: StatementWrite,
    reviewer: KadiClinicalReviewer = Depends(require_reviewer),
    db: AsyncSession = Depends(get_db),
):
    review = await _reviewer_in_review(db, reviewer, review_id)
    stmt = await service.create_statement(
        db, reviewer, review,
        evidence_reviewed=req.evidence_reviewed, reviewer_statement=req.reviewer_statement, limitations=req.limitations,
    )
    await db.commit()
    return statement_view(stmt, include_draft_fields=True)


@router.put("/clinical-reviews/{review_id}/statements/{statement_id}")
async def update_statement(
    review_id: str,
    statement_id: str,
    req: StatementWrite,
    reviewer: KadiClinicalReviewer = Depends(require_reviewer),
    db: AsyncSession = Depends(get_db),
):
    review = await _reviewer_in_review(db, reviewer, review_id)
    stmt = await service.update_statement(
        db, reviewer, review, statement_id,
        evidence_reviewed=req.evidence_reviewed, reviewer_statement=req.reviewer_statement, limitations=req.limitations,
    )
    await db.commit()
    return statement_view(stmt, include_draft_fields=True)


@router.post("/clinical-reviews/{review_id}/statements/{statement_id}/submit")
async def submit_statement(review_id: str, statement_id: str, reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)):
    review = await _reviewer_in_review(db, reviewer, review_id)
    stmt = await service.submit_statement(db, reviewer, review, statement_id)
    await db.commit()
    return statement_view(stmt, include_draft_fields=True)


@router.post("/clinical-reviews/{review_id}/statements/{statement_id}/return-to-draft")
async def return_statement_to_draft(review_id: str, statement_id: str, reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)):
    review = await _reviewer_in_review(db, reviewer, review_id)
    stmt = await service.return_to_draft(db, reviewer, review, statement_id)
    await db.commit()
    return statement_view(stmt, include_draft_fields=True)


@router.post("/clinical-reviews/{review_id}/statements/{statement_id}/finalize")
async def finalize_statement(
    review_id: str,
    statement_id: str,
    req: ConfirmRequest,
    reviewer: KadiClinicalReviewer = Depends(require_reviewer),
    db: AsyncSession = Depends(get_db),
):
    """Requires the reviewer's own credential AND the exact confirmation sentence. There is
    no server-side path that supplies either on the reviewer's behalf."""
    review = await _reviewer_in_review(db, reviewer, review_id)
    stmt = await service.finalize_statement(
        db, reviewer, review, statement_id, confirmation=req.confirmation, confirmation_text=req.confirmation_text
    )
    await db.commit()
    return statement_view(stmt)


@router.post("/clinical-reviews/{review_id}/statements/{statement_id}/revise", status_code=status.HTTP_201_CREATED)
async def revise_statement(review_id: str, statement_id: str, reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)):
    review = await _reviewer_in_review(db, reviewer, review_id)
    draft = await service.revise_statement(db, reviewer, review, statement_id)
    await db.commit()
    return statement_view(draft, include_draft_fields=True)


@router.post("/clinical-reviews/{review_id}/statements/{statement_id}/withdraw")
async def withdraw_statement(
    review_id: str,
    statement_id: str,
    req: WithdrawRequest,
    reviewer: KadiClinicalReviewer = Depends(require_reviewer),
    db: AsyncSession = Depends(get_db),
):
    review = await _reviewer_in_review(db, reviewer, review_id)
    stmt = await service.withdraw_statement(db, reviewer, review, statement_id, req.reason)
    await db.commit()
    return statement_view(stmt)


@router.post("/clinical-reviews/{review_id}/facts/{fact_id}/decision")
async def decide_fact(
    review_id: str,
    fact_id: str,
    req: FactDecisionRequest,
    reviewer: KadiClinicalReviewer = Depends(require_reviewer),
    db: AsyncSession = Depends(get_db),
):
    review = await _reviewer_in_review(db, reviewer, review_id)
    fact = await service.decide_fact(
        db, reviewer, review, fact_id,
        decision=req.decision, note=req.note, confirmation=req.confirmation, confirmation_text=req.confirmation_text,
    )
    await db.commit()
    return fact_view(fact)


@router.get("/clinical-reviews/{review_id}/audit")
async def reviewer_review_audit(review_id: str, reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)):
    review = await service.reviewer_review(db, reviewer, review_id, need_evidence_access=False)
    return await events_for_review(db, review.id)
