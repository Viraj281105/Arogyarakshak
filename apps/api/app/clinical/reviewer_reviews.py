"""Clinical review — reviewer side: queue, accept/decline with conflict-of-interest
disclosure, evidence access (ADR-011). Requires review.assigned_reviewer_id == reviewer."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kadi.clinical_review import (
    ActorType,
    AuditEventType,
    ConflictOfInterest,
    ReviewStatus,
    StatementStatus,
)
from kadi.clinical_review.lifecycle import (
    MAX_DISCLOSURE_CHARS,
    LifecycleError,
    clean_text,
)

from app.clinical.audit import record_event
from app.models import (
    KadiCase,
    KadiClinicalReview,
    KadiClinicalReviewer,
)
from app.clinical.case_reviews import statements_for_review
from app.clinical.review_common import NOT_FOUND, _lifecycle_http


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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))
    if coi == ConflictOfInterest.OTHER.value and not disclosure:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
