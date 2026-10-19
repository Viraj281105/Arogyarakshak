"""Clinical statement lifecycle: draft, edit, submit, return, finalize, revise, withdraw
(ADR-011). Statements are immutable once finalized; changes notify dependants."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from kadi.clinical_review import (
    AuditEventType,
    ReviewStatus,
    ReviewType,
    StatementStatus,
)
from kadi.clinical_review.lifecycle import (
    FINALIZATION_CONFIRMATION_TEXT,
    MAX_LIMITATIONS_CHARS,
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

from app.clinical.events import notify_statements_changed
from app.clinical.serializers import reviewer_snapshot
from app.models import (
    KadiClinicalReview,
    KadiClinicalReviewer,
    KadiClinicalStatement,
)
from app.clinical.case_reviews import statements_for_review
from app.clinical.review_common import _lifecycle_http, _new_id
from app.clinical.reviewer_reviews import _event


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
    await notify_statements_changed(db, review.case_id, review.source_module)
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
    await notify_statements_changed(db, review.case_id, review.source_module)
    return stmt
