"""
Clinical safety governance service (ADR-011).

Lifecycle: DRAFT -> UNDER_REVIEW -> APPROVED -> ACTIVE -> SUPERSEDED | RETIRED.
- Only DRAFT is editable. Submitting freezes a content hash; approvals are recorded
  against that exact hash, so editing after approval can never ride on old approvals.
- Approval is four-eyes: the proposer's own approval never counts.
- Activation supersedes the previous ACTIVE version of the same rule_key; nothing is
  deleted, every version stays auditable.
"""

import re
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kadi.clinical_review import ActorType, AuditEventType
from kadi.clinical_review.safety import (
    RuleStatus,
    RuleValidationError,
    approvals_satisfied,
    ensure_rule_transition,
    rule_content_hash,
    validate_action,
    validate_trigger,
)

from app.clinical.audit import record_event
from app.clinical.serializers import reviewer_snapshot
from app.config import settings
from app.models import KadiClinicalAuditEvent, KadiClinicalReviewer, KadiSafetyRule, KadiSafetyRuleApproval

_RULE_KEY = re.compile(r"^[a-z0-9][a-z0-9_\-]{2,60}$")
OPEN_RULE_STATES = (RuleStatus.DRAFT.value, RuleStatus.UNDER_REVIEW.value, RuleStatus.APPROVED.value)


def _http(e: Exception, code: int = status.HTTP_422_UNPROCESSABLE_ENTITY) -> HTTPException:
    return HTTPException(status_code=code, detail=str(e))


def _content_fields(rule: KadiSafetyRule) -> Dict[str, Any]:
    return {
        "rule_key": rule.rule_key,
        "version": rule.version,
        "title": rule.title,
        "description": rule.description,
        "trigger": rule.trigger,
        "action": rule.action,
        "source_name": rule.source_name,
        "source_reference": rule.source_reference,
        "source_version": rule.source_version,
        "source_section": rule.source_section,
        "limitations": rule.limitations,
        "effective_date": rule.effective_date,
        "review_due_date": rule.review_due_date,
        "changelog": rule.changelog,
    }


def _audit(db, rule: KadiSafetyRule, event: AuditEventType, actor: KadiClinicalReviewer, details=None):
    record_event(
        db,
        event_type=event.value,
        subject_type="SAFETY_RULE",
        subject_id=rule.id,
        actor_type=ActorType.REVIEWER.value,
        actor_id=actor.id,
        details={"rule_key": rule.rule_key, "version": rule.version, **(details or {})},
    )


def _text(value: Optional[str], field: str, max_chars: int, required: bool = True) -> Optional[str]:
    cleaned = (value or "").strip()
    if required and not cleaned:
        raise HTTPException(status_code=422, detail=f"{field} is required.")
    if len(cleaned) > max_chars:
        raise HTTPException(status_code=422, detail=f"{field} exceeds {max_chars} characters.")
    return cleaned or None


def _apply_fields(rule: KadiSafetyRule, data: Dict[str, Any]) -> None:
    try:
        rule.trigger = validate_trigger(data["trigger"])
        rule.action = validate_action(data["action"])
    except RuleValidationError as e:
        raise _http(e)
    rule.title = _text(data.get("title"), "title", 160)
    rule.description = _text(data.get("description"), "description", 2000)
    rule.source_name = _text(data.get("source_name"), "source_name", 300)
    rule.source_reference = _text(data.get("source_reference"), "source_reference", 500, required=False)
    rule.source_version = _text(data.get("source_version"), "source_version", 120, required=False)
    rule.source_section = _text(data.get("source_section"), "source_section", 200, required=False)
    rule.limitations = _text(data.get("limitations"), "limitations", 2000)
    rule.changelog = _text(data.get("changelog"), "changelog", 2000, required=False)
    effective = data.get("effective_date")
    review_due = data.get("review_due_date")
    if review_due is None:
        raise HTTPException(status_code=422, detail="review_due_date is required: every rule must be re-reviewed.")
    if effective and review_due <= effective:
        raise HTTPException(status_code=422, detail="review_due_date must be after effective_date.")
    rule.effective_date = effective
    rule.review_due_date = review_due


async def create_rule(db: AsyncSession, proposer: KadiClinicalReviewer, data: Dict[str, Any], *, is_demo: bool = False) -> KadiSafetyRule:
    key = (data.get("rule_key") or "").strip()
    if not _RULE_KEY.match(key):
        raise HTTPException(status_code=422, detail="rule_key must be a lowercase slug (3-61 chars).")
    existing = await db.execute(select(func.count()).select_from(KadiSafetyRule).where(KadiSafetyRule.rule_key == key))
    if existing.scalar_one():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A rule with this rule_key exists. Create a new version of it instead.",
        )
    rule = KadiSafetyRule(
        id=f"SR-{uuid.uuid4().hex[:12]}",
        rule_key=key,
        version=1,
        status=RuleStatus.DRAFT.value,
        proposed_by=proposer.id,
        required_approvals=max(1, settings.safety_rule_required_approvals),
        is_demo=is_demo,
    )
    _apply_fields(rule, data)
    db.add(rule)
    _audit(db, rule, AuditEventType.RULE_PROPOSED, proposer)
    return rule


async def get_rule(db: AsyncSession, rule_id: str) -> KadiSafetyRule:
    rule = await db.get(KadiSafetyRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Safety rule not found.")
    return rule


async def update_rule(db, actor: KadiClinicalReviewer, rule: KadiSafetyRule, data: Dict[str, Any]) -> KadiSafetyRule:
    if rule.status != RuleStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A rule in state {rule.status} is immutable. Create a new version to change it.",
        )
    if rule.proposed_by != actor.id:
        raise HTTPException(status_code=403, detail="Only the proposer can edit a draft rule.")
    _apply_fields(rule, data)
    _audit(db, rule, AuditEventType.RULE_EDITED, actor)
    return rule


async def _submission_round(db: AsyncSession, rule: KadiSafetyRule) -> int:
    """How many times this rule has been submitted (from its own audit trail)."""
    result = await db.execute(
        select(func.count()).select_from(KadiClinicalAuditEvent).where(
            KadiClinicalAuditEvent.subject_id == rule.id,
            KadiClinicalAuditEvent.event_type == AuditEventType.RULE_SUBMITTED.value,
        )
    )
    return int(result.scalar_one())


def _submitted_hash(rule: KadiSafetyRule, round_number: int) -> str:
    # The round is part of the hash so approvals belong to ONE submission: after a
    # rejection, resubmitting unchanged content yields a new hash, earlier approvals no
    # longer count, and the reviewer who rejected can decide again.
    return rule_content_hash({**_content_fields(rule), "submission_round": round_number})


async def submit_rule(db, actor: KadiClinicalReviewer, rule: KadiSafetyRule) -> KadiSafetyRule:
    if rule.proposed_by != actor.id:
        raise HTTPException(status_code=403, detail="Only the proposer can submit a draft rule for review.")
    try:
        ensure_rule_transition(rule.status, RuleStatus.UNDER_REVIEW.value)
    except RuleValidationError as e:
        raise _http(e, status.HTTP_409_CONFLICT)
    round_number = await _submission_round(db, rule) + 1
    rule.status = RuleStatus.UNDER_REVIEW.value
    rule.submitted_content_sha256 = _submitted_hash(rule, round_number)
    _audit(db, rule, AuditEventType.RULE_SUBMITTED, actor,
           {"content_sha256": rule.submitted_content_sha256, "submission_round": round_number})
    return rule


async def approvals_for(db: AsyncSession, rule: KadiSafetyRule) -> List[KadiSafetyRuleApproval]:
    rows = await db.execute(
        select(KadiSafetyRuleApproval)
        .where(KadiSafetyRuleApproval.rule_id == rule.id)
        .order_by(KadiSafetyRuleApproval.created_at)
    )
    return list(rows.scalars().all())


async def decide_rule(
    db: AsyncSession, actor: KadiClinicalReviewer, rule: KadiSafetyRule, decision: str, comment: Optional[str]
) -> KadiSafetyRule:
    if rule.status != RuleStatus.UNDER_REVIEW.value:
        raise HTTPException(status_code=409, detail=f"Rule is {rule.status}; only UNDER_REVIEW rules take decisions.")
    if decision not in ("APPROVE", "REJECT"):
        raise HTTPException(status_code=422, detail="decision must be APPROVE or REJECT.")
    if actor.id == rule.proposed_by:
        raise HTTPException(
            status_code=403,
            detail="The proposer cannot approve or reject their own rule (independent review required).",
        )
    current = [a for a in await approvals_for(db, rule) if a.content_sha256 == rule.submitted_content_sha256]
    if any(a.reviewer_id == actor.id for a in current):
        raise HTTPException(status_code=409, detail="You already recorded a decision on this version.")
    clean_comment = _text(comment, "comment", 1000, required=decision == "REJECT")
    db.add(
        KadiSafetyRuleApproval(
            id=f"SRA-{uuid.uuid4().hex[:12]}",
            rule_id=rule.id,
            reviewer_id=actor.id,
            decision=decision,
            comment=clean_comment,
            content_sha256=rule.submitted_content_sha256,
            reviewer_snapshot=reviewer_snapshot(actor),
        )
    )
    if decision == "REJECT":
        rule.status = RuleStatus.DRAFT.value
        rule.submitted_content_sha256 = None
        _audit(db, rule, AuditEventType.RULE_REJECTED, actor)
        return rule

    approvers = [a.reviewer_id for a in current if a.decision == "APPROVE"] + [actor.id]
    _audit(db, rule, AuditEventType.RULE_APPROVED, actor, {"approval_count": len(set(approvers))})
    if approvals_satisfied(approvers, rule.proposed_by, rule.required_approvals):
        rule.status = RuleStatus.APPROVED.value
    return rule


async def activate_rule(db, actor: KadiClinicalReviewer, rule: KadiSafetyRule) -> KadiSafetyRule:
    try:
        ensure_rule_transition(rule.status, RuleStatus.ACTIVE.value)
    except RuleValidationError as e:
        raise _http(e, status.HTTP_409_CONFLICT)
    await db.flush()
    if _submitted_hash(rule, await _submission_round(db, rule)) != rule.submitted_content_sha256:
        raise HTTPException(status_code=409, detail="Rule content changed after approval; it cannot be activated.")
    previous = await db.execute(
        select(KadiSafetyRule).where(
            KadiSafetyRule.rule_key == rule.rule_key,
            KadiSafetyRule.status == RuleStatus.ACTIVE.value,
            KadiSafetyRule.id != rule.id,
        )
    )
    for old in previous.scalars().all():
        old.status = RuleStatus.SUPERSEDED.value
        _audit(db, old, AuditEventType.RULE_SUPERSEDED, actor, {"superseded_by": rule.id})
    # effective_date is part of the approved content hash; activation only records when
    # and by whom, never alters what was approved.
    rule.status = RuleStatus.ACTIVE.value
    rule.activated_at = datetime.utcnow()
    rule.activated_by = actor.id
    _audit(db, rule, AuditEventType.RULE_ACTIVATED, actor)
    return rule


async def retire_rule(db, actor: KadiClinicalReviewer, rule: KadiSafetyRule, reason: Optional[str]) -> KadiSafetyRule:
    try:
        ensure_rule_transition(rule.status, RuleStatus.RETIRED.value)
    except RuleValidationError as e:
        raise _http(e, status.HTTP_409_CONFLICT)
    rule.retired_reason = _text(reason, "reason", 1000)
    rule.status = RuleStatus.RETIRED.value
    rule.retired_at = datetime.utcnow()
    rule.retired_by = actor.id
    _audit(db, rule, AuditEventType.RULE_RETIRED, actor)
    return rule


async def new_version(db, actor: KadiClinicalReviewer, rule: KadiSafetyRule) -> KadiSafetyRule:
    open_versions = await db.execute(
        select(func.count()).select_from(KadiSafetyRule).where(
            KadiSafetyRule.rule_key == rule.rule_key, KadiSafetyRule.status.in_(OPEN_RULE_STATES)
        )
    )
    if open_versions.scalar_one():
        raise HTTPException(status_code=409, detail="This rule already has a version in progress.")
    latest = await db.execute(select(func.max(KadiSafetyRule.version)).where(KadiSafetyRule.rule_key == rule.rule_key))
    draft = KadiSafetyRule(
        id=f"SR-{uuid.uuid4().hex[:12]}",
        rule_key=rule.rule_key,
        version=(latest.scalar_one() or rule.version) + 1,
        status=RuleStatus.DRAFT.value,
        proposed_by=actor.id,
        required_approvals=max(1, settings.safety_rule_required_approvals),
        supersedes_rule_id=rule.id,
        title=rule.title,
        description=rule.description,
        trigger=rule.trigger,
        action=rule.action,
        source_name=rule.source_name,
        source_reference=rule.source_reference,
        source_version=rule.source_version,
        source_section=rule.source_section,
        limitations=rule.limitations,
        effective_date=None,
        review_due_date=rule.review_due_date,
        changelog=None,
    )
    db.add(draft)
    _audit(db, draft, AuditEventType.RULE_PROPOSED, actor, {"from_version": rule.version})
    return draft


async def rule_view(db: AsyncSession, rule: KadiSafetyRule) -> Dict[str, Any]:
    approvals = await approvals_for(db, rule)
    proposer = await db.get(KadiClinicalReviewer, rule.proposed_by)
    return {
        "rule_id": rule.id,
        "rule_key": rule.rule_key,
        "version": rule.version,
        "title": rule.title,
        "description": rule.description,
        "trigger": rule.trigger,
        "action": rule.action,
        "source": {
            "name": rule.source_name,
            "reference": rule.source_reference,
            "version": rule.source_version,
            "section": rule.source_section,
        },
        "limitations": rule.limitations,
        "status": rule.status,
        "is_demo": rule.is_demo,
        "proposed_by": reviewer_snapshot(proposer) if proposer else None,
        "required_approvals": rule.required_approvals,
        "approvals": [
            {
                "decision": a.decision,
                "comment": a.comment,
                "reviewer": a.reviewer_snapshot,
                "content_sha256": a.content_sha256,
                "applies_to_current_content": a.content_sha256 == rule.submitted_content_sha256,
                "created_at": a.created_at,
            }
            for a in approvals
        ],
        "submitted_content_sha256": rule.submitted_content_sha256,
        "effective_date": rule.effective_date,
        "review_due_date": rule.review_due_date,
        "review_overdue": bool(rule.review_due_date and rule.review_due_date < date.today() and rule.status == "ACTIVE"),
        "changelog": rule.changelog,
        "supersedes_rule_id": rule.supersedes_rule_id,
        "activated_at": rule.activated_at,
        "retired_at": rule.retired_at,
        "retired_reason": rule.retired_reason,
        "created_at": rule.created_at,
    }
