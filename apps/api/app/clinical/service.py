"""
Clinical review service: requests, assignment, COI, evidence access, statements and
fact confirmations (ADR-011).

Authorization is object-level at every step, never inferred from an id:
- case-holder operations load the review by (case_id, review_id) after the case token
  was verified, so a review id from another case is simply "not found";
- reviewer operations require review.assigned_reviewer_id == this reviewer, the review
  in an accessible state, and the case still existing with consent;
- statement operations additionally require statement.reviewer_id == this reviewer.
"Not yours" is reported as 404 so ids cannot be probed; "yours, wrong state" is 409.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kadi.clinical_review import (
    ActorType,
    AuditEventType,
    CLINICAL_JUDGMENT_CATEGORIES_VALUES,
    ConflictOfInterest,
    FactDecision,
    ReviewStatus,
    ReviewType,
    StatementStatus,
)
from kadi.clinical_review.evidence import (
    EntityRecord,
    SupplementaryItem,
    build_coi_context,
    build_evidence_packet,
    resolve_scope,
)
from kadi.clinical_review.lifecycle import (
    FACT_DECISION_CONFIRMATION_TEXT,
    FINALIZATION_CONFIRMATION_TEXT,
    MAX_DISCLOSURE_CHARS,
    MAX_LIMITATIONS_CHARS,
    MAX_QUESTION_CHARS,
    MAX_STATEMENT_CHARS,
    LifecycleError,
    clean_text,
    ensure_editable,
    ensure_finalizable,
    ensure_revisable,
    ensure_submittable,
    ensure_withdrawable,
    hashed_statement_fields,
    require_confirmation,
    statement_content_hash,
    validate_evidence_selection,
)

from app.clinical.audit import record_event
from app.clinical.serializers import reviewer_snapshot
from app.consent import require_case_consent
from app.models import (
    KadiCase,
    KadiClinicalFactConfirmation,
    KadiClinicalReview,
    KadiClinicalReviewer,
    KadiClinicalStatement,
)

NOT_FOUND = "Clinical review not found."


def _lifecycle_http(e: LifecycleError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# --- Case-holder side ---------------------------------------------------------

async def create_review(
    db: AsyncSession,
    case: KadiCase,
    *,
    source_module: str,
    review_type: str,
    clinical_question: str,
    entities: Sequence[EntityRecord],
    evidence_scope: Optional[Sequence[str]],
    insurer_name: Optional[str],
    trigger: str,
    trigger_ref: Optional[str],
    share_with_reviewer_consent: bool,
    supplementary: Sequence[SupplementaryItem] = (),
    facts: Sequence[Dict[str, Optional[str]]] = (),
) -> KadiClinicalReview:
    require_case_consent(case)
    if share_with_reviewer_consent is not True:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Sharing case evidence with a human reviewer needs the patient's explicit "
                "agreement for this request: set share_with_reviewer_consent to true."
            ),
        )
    try:
        question = clean_text(clinical_question, max_chars=MAX_QUESTION_CHARS, field="clinical_question")
        scope = resolve_scope(source_module, evidence_scope)
    except LifecycleError as e:
        raise _lifecycle_http(e)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    packet = build_evidence_packet(entities, scope, supplementary)
    if not packet:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "There is no case evidence of the selected types to share with a reviewer. "
                "Upload the relevant document first or widen evidence_scope."
            ),
        )

    review = KadiClinicalReview(
        id=_new_id("CR"),
        case_id=case.id,
        source_module=source_module,
        review_type=review_type,
        status=ReviewStatus.REQUESTED.value,
        clinical_question=question,
        trigger=trigger,
        trigger_ref=trigger_ref,
        evidence_scope=scope,
        evidence_packet=packet,
        coi_context=build_coi_context(entities, source_module, insurer_name),
        insurer_name=insurer_name,
        consent_confirmed_at=datetime.utcnow(),
    )
    db.add(review)
    for fact in facts:
        db.add(
            KadiClinicalFactConfirmation(
                id=_new_id("CF"),
                review_id=review.id,
                case_id=case.id,
                fact_key=fact["fact_key"],
                fact_question=fact["question"],
                source=fact.get("source") or source_module,
                playbook_ref=fact.get("playbook_ref"),
                decision=FactDecision.PENDING.value,
            )
        )
    record_event(
        db,
        event_type=AuditEventType.REVIEW_REQUESTED.value,
        subject_type="REVIEW",
        subject_id=review.id,
        actor_type=ActorType.CASE_HOLDER.value,
        case_id=case.id,
        review_id=review.id,
        details={
            "source_module": source_module,
            "review_type": review_type,
            "trigger": trigger,
            "evidence_item_count": len(packet),
            "evidence_scope": scope,
            "fact_count": len(facts),
        },
    )
    return review


async def get_case_review(db: AsyncSession, case_id: str, review_id: str) -> KadiClinicalReview:
    review = await db.get(KadiClinicalReview, review_id)
    if review is None or review.case_id != case_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return review


async def list_case_reviews(db: AsyncSession, case_id: str) -> List[KadiClinicalReview]:
    rows = await db.execute(
        select(KadiClinicalReview)
        .where(KadiClinicalReview.case_id == case_id)
        .order_by(KadiClinicalReview.created_at)
    )
    return list(rows.scalars().all())


async def assign_review(
    db: AsyncSession, case: KadiCase, review: KadiClinicalReview, reviewer_id: str
) -> KadiClinicalReviewer:
    require_case_consent(case)
    if review.status not in (ReviewStatus.REQUESTED.value, ReviewStatus.DECLINED.value, ReviewStatus.ASSIGNED.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A review in state {review.status} cannot be (re)assigned.",
        )
    reviewer = await db.get(KadiClinicalReviewer, reviewer_id)
    if reviewer is None or not reviewer.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reviewer not found.")
    if reviewer.category not in CLINICAL_JUDGMENT_CATEGORIES_VALUES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "This review asks for clinical judgment, which needs a reviewer registered as a "
                "doctor. Pharmacists, transcriptionists and annotators can resolve transcription "
                "tasks instead."
            ),
        )
    review.assigned_reviewer_id = reviewer.id
    review.assigned_at = datetime.utcnow()
    review.accepted_at = None
    review.coi_category = None
    review.coi_disclosure = None
    review.coi_declared_at = None
    review.decline_reason = None
    review.status = ReviewStatus.ASSIGNED.value
    record_event(
        db,
        event_type=AuditEventType.REVIEWER_ASSIGNED.value,
        subject_type="REVIEW",
        subject_id=review.id,
        actor_type=ActorType.CASE_HOLDER.value,
        case_id=case.id,
        review_id=review.id,
        details={"reviewer_id": reviewer.id, "verification_status": reviewer.verification_status},
    )
    return reviewer


async def cancel_review(db: AsyncSession, case: KadiCase, review: KadiClinicalReview) -> None:
    if review.status == ReviewStatus.CANCELLED.value:
        return
    review.status = ReviewStatus.CANCELLED.value
    review.cancelled_at = datetime.utcnow()
    record_event(
        db,
        event_type=AuditEventType.REVIEW_CANCELLED.value,
        subject_type="REVIEW",
        subject_id=review.id,
        actor_type=ActorType.CASE_HOLDER.value,
        case_id=case.id,
        review_id=review.id,
        details={"reviewer_access_revoked": True},
    )


async def statements_for_review(db: AsyncSession, review_id: str) -> List[KadiClinicalStatement]:
    rows = await db.execute(
        select(KadiClinicalStatement)
        .where(KadiClinicalStatement.review_id == review_id)
        .order_by(KadiClinicalStatement.statement_version, KadiClinicalStatement.created_at)
    )
    return list(rows.scalars().all())


async def facts_for_review(db: AsyncSession, review_id: str) -> List[KadiClinicalFactConfirmation]:
    rows = await db.execute(
        select(KadiClinicalFactConfirmation)
        .where(KadiClinicalFactConfirmation.review_id == review_id)
        .order_by(KadiClinicalFactConfirmation.created_at)
    )
    return list(rows.scalars().all())


async def current_statements_for_case(
    db: AsyncSession, case_id: str, source_modules: Sequence[str]
) -> List[KadiClinicalStatement]:
    """FINALIZED statements whose review was not cancelled — the only ones any package may
    present as a current human opinion."""
    rows = await db.execute(
        select(KadiClinicalStatement)
        .join(KadiClinicalReview, KadiClinicalReview.id == KadiClinicalStatement.review_id)
        .where(
            KadiClinicalStatement.case_id == case_id,
            KadiClinicalStatement.status == StatementStatus.FINALIZED.value,
            KadiClinicalReview.case_id == case_id,
            KadiClinicalReview.status != ReviewStatus.CANCELLED.value,
            KadiClinicalReview.source_module.in_(list(source_modules)),
        )
        .order_by(KadiClinicalStatement.finalized_at)
    )
    return list(rows.scalars().all())


# --- Reviewer side -------------------------------------------------------------

REVIEWER_VISIBLE_STATES = frozenset(
    {ReviewStatus.ASSIGNED.value, ReviewStatus.IN_REVIEW.value, ReviewStatus.COMPLETED.value}
)
EVIDENCE_STATES = frozenset({ReviewStatus.IN_REVIEW.value, ReviewStatus.COMPLETED.value})


async def reviewer_review(
    db: AsyncSession, reviewer: KadiClinicalReviewer, review_id: str, *, need_evidence_access: bool
) -> KadiClinicalReview:
    review = await db.get(KadiClinicalReview, review_id)
    if (
        review is None
        or review.assigned_reviewer_id != reviewer.id
        or review.status not in REVIEWER_VISIBLE_STATES
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    case = await db.get(KadiCase, review.case_id)
    if case is None or not case.consent_opt_in:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    if need_evidence_access and (review.status not in EVIDENCE_STATES or not review.coi_declared_at):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Accept the review and declare any conflict of interest before opening the evidence.",
        )
    return review


async def reviewer_queue(db: AsyncSession, reviewer: KadiClinicalReviewer) -> List[KadiClinicalReview]:
    rows = await db.execute(
        select(KadiClinicalReview)
        .where(
            KadiClinicalReview.assigned_reviewer_id == reviewer.id,
            KadiClinicalReview.status.in_(list(REVIEWER_VISIBLE_STATES)),
        )
        .order_by(KadiClinicalReview.created_at)
    )
    return list(rows.scalars().all())


def _event(db, review: KadiClinicalReview, reviewer: KadiClinicalReviewer, event: AuditEventType, subject_type: str, subject_id: str, details=None):
    record_event(
        db,
        event_type=event.value,
        subject_type=subject_type,
        subject_id=subject_id,
        actor_type=ActorType.REVIEWER.value,
        actor_id=reviewer.id,
        case_id=review.case_id,
        review_id=review.id,
        details=details,
    )


async def accept_review(
    db: AsyncSession,
    reviewer: KadiClinicalReviewer,
    review: KadiClinicalReview,
    coi_category: str,
    coi_disclosure: Optional[str],
) -> None:
    if review.status != ReviewStatus.ASSIGNED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Review is {review.status}, not awaiting acceptance.")
    try:
        coi = ConflictOfInterest(coi_category).value
        disclosure = clean_text(coi_disclosure, max_chars=MAX_DISCLOSURE_CHARS, field="coi_disclosure", required=False)
    except (ValueError, LifecycleError) as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    if coi == ConflictOfInterest.OTHER.value and not disclosure:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A conflict of interest of type OTHER needs a written disclosure.",
        )
    now = datetime.utcnow()
    review.coi_category = coi
    review.coi_disclosure = disclosure
    review.coi_declared_at = now
    review.accepted_at = now
    review.status = ReviewStatus.IN_REVIEW.value
    _event(db, review, reviewer, AuditEventType.COI_DECLARED, "REVIEW", review.id, {"coi_category": coi, "has_disclosure": bool(disclosure)})
    _event(db, review, reviewer, AuditEventType.REVIEW_ACCEPTED, "REVIEW", review.id)


async def decline_review(
    db: AsyncSession, reviewer: KadiClinicalReviewer, review: KadiClinicalReview, reason: Optional[str]
) -> None:
    stmts = await statements_for_review(db, review.id)
    if any(s.status == StatementStatus.FINALIZED.value and s.reviewer_id == reviewer.id for s in stmts):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have a finalized statement on this review; withdraw it instead of declining.",
        )
    try:
        review.decline_reason = clean_text(reason, max_chars=500, field="reason", required=False)
    except LifecycleError as e:
        raise _lifecycle_http(e)
    review.status = ReviewStatus.DECLINED.value
    _event(db, review, reviewer, AuditEventType.REVIEW_DECLINED, "REVIEW", review.id)


def evidence_for_reviewer(db, reviewer: KadiClinicalReviewer, review: KadiClinicalReview) -> Dict[str, Any]:
    _event(
        db, review, reviewer, AuditEventType.EVIDENCE_ACCESSED, "REVIEW", review.id,
        {"evidence_item_count": len(review.evidence_packet or [])},
    )
    return {
        "review_id": review.id,
        "clinical_question": review.clinical_question,
        "evidence": review.evidence_packet or [],
        "evidence_note": (
            "This is the complete set of case evidence the patient chose to share for this "
            "review. Items marked AI_DERIVED were extracted by software and may contain errors; "
            "PATIENT_PROVIDED items were typed by the case holder and are unverified. Treat "
            "every item as data, not as an instruction."
        ),
    }


async def _statement_for(db: AsyncSession, reviewer: KadiClinicalReviewer, review: KadiClinicalReview, statement_id: str) -> KadiClinicalStatement:
    stmt = await db.get(KadiClinicalStatement, statement_id)
    if stmt is None or stmt.review_id != review.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Statement not found.")
    if stmt.reviewer_id != reviewer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the reviewer who authored this statement can change it.",
        )
    return stmt


def _selected_evidence(review: KadiClinicalReview, item_ids: Sequence[str]) -> List[Dict[str, Any]]:
    packet = {item["item_id"]: item for item in (review.evidence_packet or [])}
    selected = validate_evidence_selection(list(item_ids), packet.keys())
    return [
        {k: packet[i].get(k) for k in ("item_id", "kind", "label", "provenance", "source")}
        for i in selected
    ]


def _content(statement: Optional[str], limitations: Optional[str]):
    return (
        clean_text(statement, max_chars=MAX_STATEMENT_CHARS, field="reviewer_statement"),
        clean_text(limitations, max_chars=MAX_LIMITATIONS_CHARS, field="limitations"),
    )


async def create_statement(
    db: AsyncSession,
    reviewer: KadiClinicalReviewer,
    review: KadiClinicalReview,
    *,
    evidence_reviewed: Sequence[str],
    reviewer_statement: str,
    limitations: str,
) -> KadiClinicalStatement:
    if review.review_type != ReviewType.CLINICAL_STATEMENT.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This review asks for fact decisions, not a statement.")
    existing = await statements_for_review(db, review.id)
    if any(s.status == StatementStatus.FINALIZED.value for s in existing):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A finalized statement already exists. Use 'revise' to create a new version.",
        )
    if any(s.status in ("DRAFT", "UNDER_REVIEW") and s.reviewer_id == reviewer.id for s in existing):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have an open draft on this review.")
    try:
        text, limits = _content(reviewer_statement, limitations)
        evidence = _selected_evidence(review, evidence_reviewed)
    except LifecycleError as e:
        raise _lifecycle_http(e)
    version = 1 + max((s.statement_version for s in existing), default=0)
    stmt = KadiClinicalStatement(
        id=_new_id("CS"),
        review_id=review.id,
        case_id=review.case_id,
        reviewer_id=reviewer.id,
        statement_version=version,
        clinical_question=review.clinical_question,
        evidence_reviewed=evidence,
        reviewer_statement=text,
        limitations=limits,
        coi_category=review.coi_category,
        coi_disclosure=review.coi_disclosure,
        status=StatementStatus.DRAFT.value,
    )
    db.add(stmt)
    _event(db, review, reviewer, AuditEventType.STATEMENT_CREATED, "STATEMENT", stmt.id, {"statement_version": version})
    return stmt


async def update_statement(
    db: AsyncSession,
    reviewer: KadiClinicalReviewer,
    review: KadiClinicalReview,
    statement_id: str,
    *,
    evidence_reviewed: Sequence[str],
    reviewer_statement: str,
    limitations: str,
) -> KadiClinicalStatement:
    stmt = await _statement_for(db, reviewer, review, statement_id)
    try:
        ensure_editable(stmt.status)
        text, limits = _content(reviewer_statement, limitations)
        evidence = _selected_evidence(review, evidence_reviewed)
    except LifecycleError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT if "cannot be edited" in str(e) else 422, detail=str(e)
        )
    stmt.reviewer_statement = text
    stmt.limitations = limits
    stmt.evidence_reviewed = evidence
    _event(db, review, reviewer, AuditEventType.STATEMENT_EDITED, "STATEMENT", stmt.id, {"statement_version": stmt.statement_version})
    return stmt


async def submit_statement(db, reviewer, review, statement_id) -> KadiClinicalStatement:
    stmt = await _statement_for(db, reviewer, review, statement_id)
    try:
        ensure_submittable(stmt.status)
    except LifecycleError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    stmt.status = StatementStatus.UNDER_REVIEW.value
    _event(db, review, reviewer, AuditEventType.STATEMENT_SUBMITTED, "STATEMENT", stmt.id, {"statement_version": stmt.statement_version})
    return stmt


async def return_to_draft(db, reviewer, review, statement_id) -> KadiClinicalStatement:
    stmt = await _statement_for(db, reviewer, review, statement_id)
    if stmt.status != StatementStatus.UNDER_REVIEW.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only an UNDER_REVIEW statement can return to DRAFT.")
    stmt.status = StatementStatus.DRAFT.value
    _event(db, review, reviewer, AuditEventType.STATEMENT_EDITED, "STATEMENT", stmt.id, {"returned_to_draft": True})
    return stmt


async def finalize_statement(
    db: AsyncSession,
    reviewer: KadiClinicalReviewer,
    review: KadiClinicalReview,
    statement_id: str,
    *,
    confirmation: bool,
    confirmation_text: Optional[str],
) -> KadiClinicalStatement:
    stmt = await _statement_for(db, reviewer, review, statement_id)
    try:
        ensure_finalizable(stmt.status)
    except LifecycleError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    try:
        require_confirmation(confirmation, confirmation_text, FINALIZATION_CONFIRMATION_TEXT)
    except LifecycleError as e:
        raise _lifecycle_http(e)

    now = datetime.utcnow()
    snapshot = reviewer_snapshot(reviewer)
    previous = [
        s for s in await statements_for_review(db, review.id)
        if s.status == StatementStatus.FINALIZED.value and s.id != stmt.id
    ]
    stmt.reviewer_snapshot = snapshot
    stmt.confirmation_text = FINALIZATION_CONFIRMATION_TEXT
    stmt.confirmed_at = now
    stmt.finalized_at = now
    stmt.status = StatementStatus.FINALIZED.value
    stmt.content_sha256 = statement_content_hash(
        hashed_statement_fields(
            statement_id=stmt.id,
            review_id=review.id,
            case_id=review.case_id,
            reviewer_id=reviewer.id,
            version=stmt.statement_version,
            clinical_question=stmt.clinical_question,
            evidence_reviewed=stmt.evidence_reviewed,
            reviewer_statement=stmt.reviewer_statement,
            limitations=stmt.limitations,
            coi_category=stmt.coi_category,
            coi_disclosure=stmt.coi_disclosure,
            reviewer_snapshot=snapshot,
            confirmation_text=FINALIZATION_CONFIRMATION_TEXT,
        )
    )
    for old in previous:
        old.status = StatementStatus.SUPERSEDED.value
        _event(db, review, reviewer, AuditEventType.STATEMENT_SUPERSEDED, "STATEMENT", old.id,
               {"superseded_by": stmt.id, "statement_version": old.statement_version})
    review.status = ReviewStatus.COMPLETED.value
    review.completed_at = now
    _event(
        db, review, reviewer, AuditEventType.STATEMENT_FINALIZED, "STATEMENT", stmt.id,
        {
            "statement_version": stmt.statement_version,
            "content_sha256": stmt.content_sha256,
            "evidence_item_count": len(stmt.evidence_reviewed or []),
            "verification_status": reviewer.verification_status,
            "coi_category": stmt.coi_category,
        },
    )
    return stmt


async def revise_statement(db, reviewer, review, statement_id) -> KadiClinicalStatement:
    stmt = await _statement_for(db, reviewer, review, statement_id)
    try:
        ensure_revisable(stmt.status)
    except LifecycleError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    existing = await statements_for_review(db, review.id)
    if any(s.status in ("DRAFT", "UNDER_REVIEW") and s.reviewer_id == reviewer.id for s in existing):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have an open draft on this review.")
    draft = KadiClinicalStatement(
        id=_new_id("CS"),
        review_id=review.id,
        case_id=review.case_id,
        reviewer_id=reviewer.id,
        statement_version=max(s.statement_version for s in existing) + 1,
        supersedes_statement_id=stmt.id,
        clinical_question=stmt.clinical_question,
        evidence_reviewed=list(stmt.evidence_reviewed or []),
        reviewer_statement=stmt.reviewer_statement,
        limitations=stmt.limitations,
        coi_category=review.coi_category or stmt.coi_category,
        coi_disclosure=review.coi_disclosure,
        status=StatementStatus.DRAFT.value,
    )
    db.add(draft)
    _event(db, review, reviewer, AuditEventType.STATEMENT_CREATED, "STATEMENT", draft.id,
           {"statement_version": draft.statement_version, "revises": stmt.id})
    return draft


async def withdraw_statement(db, reviewer, review, statement_id, reason: Optional[str]) -> KadiClinicalStatement:
    stmt = await _statement_for(db, reviewer, review, statement_id)
    try:
        ensure_withdrawable(stmt.status)
        clean_reason = clean_text(reason, max_chars=500, field="reason")
    except LifecycleError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT if "Only" in str(e) else 422, detail=str(e))
    stmt.status = StatementStatus.WITHDRAWN.value
    stmt.withdrawn_reason = clean_reason
    stmt.withdrawn_at = datetime.utcnow()
    review.status = ReviewStatus.IN_REVIEW.value
    review.completed_at = None
    _event(db, review, reviewer, AuditEventType.STATEMENT_WITHDRAWN, "STATEMENT", stmt.id, {"statement_version": stmt.statement_version})
    return stmt


async def decide_fact(
    db: AsyncSession,
    reviewer: KadiClinicalReviewer,
    review: KadiClinicalReview,
    fact_id: str,
    *,
    decision: str,
    note: Optional[str],
    confirmation: bool,
    confirmation_text: Optional[str],
) -> KadiClinicalFactConfirmation:
    if review.review_type != ReviewType.FACT_CONFIRMATION.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This review has no facts to decide.")
    fact = await db.get(KadiClinicalFactConfirmation, fact_id)
    if fact is None or fact.review_id != review.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fact not found.")
    if fact.decision != FactDecision.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This fact was already decided. Decisions are immutable; the case holder can request a new review.",
        )
    if decision not in (FactDecision.CONFIRMED.value, FactDecision.REJECTED.value, FactDecision.CANNOT_DETERMINE.value):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="decision must be CONFIRMED, REJECTED or CANNOT_DETERMINE.")
    try:
        require_confirmation(confirmation, confirmation_text, FACT_DECISION_CONFIRMATION_TEXT)
        clean_note = clean_text(note, max_chars=1000, field="note", required=False)
    except LifecycleError as e:
        raise _lifecycle_http(e)

    fact.decision = decision
    fact.reviewer_id = reviewer.id
    fact.reviewer_note = clean_note
    fact.reviewer_snapshot = reviewer_snapshot(reviewer)
    fact.coi_category = review.coi_category
    fact.coi_disclosure = review.coi_disclosure
    fact.confirmation_text = FACT_DECISION_CONFIRMATION_TEXT
    fact.decided_at = datetime.utcnow()
    _event(db, review, reviewer, AuditEventType.FACT_DECIDED, "FACT", fact.id, {"fact_key": fact.fact_key, "decision": decision})

    remaining = [f for f in await facts_for_review(db, review.id) if f.decision == FactDecision.PENDING.value and f.id != fact.id]
    if not remaining:
        review.status = ReviewStatus.COMPLETED.value
        review.completed_at = datetime.utcnow()
    return fact


async def latest_fact_decisions(db: AsyncSession, case_id: str) -> Dict[str, KadiClinicalFactConfirmation]:
    """Most recent non-pending decision per fact_key for the case (from non-cancelled
    reviews); a pending request is returned only when no decision exists yet."""
    rows = await db.execute(
        select(KadiClinicalFactConfirmation, KadiClinicalReview.status)
        .join(KadiClinicalReview, KadiClinicalReview.id == KadiClinicalFactConfirmation.review_id)
        .where(
            KadiClinicalFactConfirmation.case_id == case_id,
            KadiClinicalReview.case_id == case_id,
            KadiClinicalReview.status != ReviewStatus.CANCELLED.value,
        )
        .order_by(KadiClinicalFactConfirmation.created_at)
    )
    latest: Dict[str, KadiClinicalFactConfirmation] = {}
    for fact, _ in rows.all():
        current = latest.get(fact.fact_key)
        if current is None or fact.decision != FactDecision.PENDING.value or current.decision == FactDecision.PENDING.value:
            latest[fact.fact_key] = fact
    return latest
