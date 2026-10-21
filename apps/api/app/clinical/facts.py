"""Clinical fact confirmations by the assigned reviewer (ADR-011)."""

from datetime import datetime
from typing import Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kadi.clinical_review import (
    AuditEventType,
    FactDecision,
    ReviewStatus,
    ReviewType,
)
from kadi.clinical_review.lifecycle import (
    FACT_DECISION_CONFIRMATION_TEXT,
    LifecycleError,
    clean_text,
    require_confirmation,
)

from app.clinical.serializers import reviewer_snapshot
from app.models import (
    KadiClinicalFactConfirmation,
    KadiClinicalReview,
    KadiClinicalReviewer,
)
from app.clinical.case_reviews import facts_for_review
from app.clinical.review_common import _lifecycle_http
from app.clinical.reviewer_reviews import _event


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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="decision must be CONFIRMED, REJECTED or CANNOT_DETERMINE.")
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
