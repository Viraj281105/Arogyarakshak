"""Clinical review — case-holder side: request, read, assign, cancel (ADR-011).

The review is always loaded by (case_id, review_id) after the case token was verified,
so a review id from another case is simply "not found"."""

from datetime import datetime
from typing import Dict, List, Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kadi.clinical_review import (
    ActorType,
    AuditEventType,
    CLINICAL_JUDGMENT_CATEGORIES_VALUES,
    FactDecision,
    ReviewStatus,
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
    MAX_QUESTION_CHARS,
    LifecycleError,
    clean_text,
)

from app.clinical.audit import record_event
from app.clinical.auth import reviewer_available
from app.clinical.events import notify_statements_changed
from app.consent import require_case_consent
from app.models import (
    KadiCase,
    KadiClinicalFactConfirmation,
    KadiClinicalReview,
    KadiClinicalReviewer,
    KadiClinicalStatement,
)
from app.clinical.review_common import NOT_FOUND, _lifecycle_http, _new_id


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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))

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
    # The fact rows reference the review by a plain FK (no ORM relationship), so the unit of
    # work does not know to insert the review first. SQLite does not enforce FKs; Postgres
    # does, and rejected every doctor-confirmation request (found in the Postgres smoke run).
    await db.flush()
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
    if not reviewer_available(reviewer):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reviewer not found.")
    if reviewer.category not in CLINICAL_JUDGMENT_CATEGORIES_VALUES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
    await notify_statements_changed(db, case.id, review.source_module)


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
