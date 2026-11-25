"""The user's action and resolution records for a case — use cases (ADR-031).

State rules live in kadi.resolution_tracking. Free text is redacted of direct identifiers
before it is stored, no file is stored, and every entry is marked as the user's own record.
"""

import logging
import secrets
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from kadi.privacy.redaction import redact_pii
from kadi.resolution_tracking import ALLOWED_TRANSITIONS, ActionStatus, TrackingError, validate_event

from app.models import KadiCaseAction, KadiCaseActionEvent, KadiCaseDocument

logger = logging.getLogger("arogyarakshak.api.actions")

# A case is one episode of care; this is far above real use and stops unbounded growth.
MAX_ACTIONS_PER_CASE = 50
MAX_EVENTS_PER_ACTION = 100
PROVENANCE_USER = "user_recorded"


class ActionNotFound(Exception):
    pass


class TrackingLimit(TrackingError):
    pass


class ConcurrentUpdate(TrackingError):
    """Two updates to one action arrived together; the second must look again."""


def _clean(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    cleaned = redact_pii(text.strip())
    return cleaned or None


async def _events(db: AsyncSession, action_id: str) -> List[KadiCaseActionEvent]:
    result = await db.execute(
        select(KadiCaseActionEvent)
        .where(KadiCaseActionEvent.action_id == action_id)
        .order_by(KadiCaseActionEvent.sequence)
    )
    return list(result.scalars().all())


async def _action(db: AsyncSession, case_id: str, action_id: str) -> KadiCaseAction:
    result = await db.execute(
        select(KadiCaseAction).where(KadiCaseAction.id == action_id, KadiCaseAction.case_id == case_id)
    )
    action = result.scalar_one_or_none()
    if action is None:
        raise ActionNotFound()
    return action


def view(action: KadiCaseAction, events: List[KadiCaseActionEvent]) -> Dict[str, Any]:
    status = ActionStatus(action.status)
    return {
        "id": action.id,
        "module": action.module,
        "kind": action.kind,
        "title": action.title,
        "finding_ref": action.finding_ref,
        "status": action.status,
        "allowed_next": sorted(s.value for s in ALLOWED_TRANSITIONS[status]),
        "institution": action.institution,
        "contact_method": action.contact_method,
        "next_step": action.next_step,
        "amount_disputed": action.amount_disputed,
        "amount_corrected": action.amount_corrected,
        "created_at": action.created_at,
        "updated_at": action.updated_at,
        "events": [
            {
                "status": e.status,
                "occurred_on": e.occurred_on,
                "note": e.note,
                "evidence_sha256": e.evidence_sha256,
                "provenance": e.provenance,
                "recorded_at": e.created_at,
            }
            for e in events
        ],
    }


async def list_actions(db: AsyncSession, case_id: str) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(KadiCaseAction)
        .where(KadiCaseAction.case_id == case_id)
        .order_by(KadiCaseAction.created_at, KadiCaseAction.id)
    )
    actions = list(result.scalars().all())
    if not actions:
        return []
    rows = await db.execute(
        select(KadiCaseActionEvent)
        .where(KadiCaseActionEvent.case_id == case_id)
        .order_by(KadiCaseActionEvent.sequence)
    )
    by_action: Dict[str, List[KadiCaseActionEvent]] = {}
    for event in rows.scalars().all():
        by_action.setdefault(event.action_id, []).append(event)
    return [view(a, by_action.get(a.id, [])) for a in actions]


async def create_action(db: AsyncSession, case_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """Starts tracking one step. It begins as 'planned': choosing a step is not doing it. Commits."""
    count = await db.execute(select(func.count()).select_from(KadiCaseAction).where(KadiCaseAction.case_id == case_id))
    if count.scalar_one() >= MAX_ACTIONS_PER_CASE:
        raise TrackingLimit(f"A case can track at most {MAX_ACTIONS_PER_CASE} actions.")
    title = _clean(fields["title"])
    if not title:
        raise TrackingError("Give the action a title.")
    now = datetime.utcnow()
    action = KadiCaseAction(
        id=f"ACT-{secrets.token_hex(10)}",
        case_id=case_id,
        module=fields["module"],
        kind=fields["kind"],
        title=title[:200],
        finding_ref=_clean(fields.get("finding_ref")),
        status=ActionStatus.PLANNED.value,
        institution=_clean(fields.get("institution")),
        contact_method=fields.get("contact_method"),
        next_step=_clean(fields.get("next_step")),
        amount_disputed=fields.get("amount_disputed"),
        created_at=now,
        updated_at=now,
    )
    db.add(action)
    await db.flush()
    first = KadiCaseActionEvent(
        id=f"EVT-{secrets.token_hex(10)}",
        action_id=action.id,
        case_id=case_id,
        sequence=1,
        status=ActionStatus.PLANNED.value,
        provenance=PROVENANCE_USER,
        created_at=now,
    )
    db.add(first)
    await db.commit()
    logger.info("Action %s (%s) added to case %s.", action.id, action.module, case_id)
    return view(action, [first])


async def record_event(
    db: AsyncSession, case_id: str, action_id: str, fields: Dict[str, Any], today: Optional[date] = None
) -> Dict[str, Any]:
    """Appends what the user says happened and moves the action accordingly. Commits."""
    action = await _action(db, case_id, action_id)
    events = await _events(db, action_id)
    if len(events) >= MAX_EVENTS_PER_ACTION:
        raise TrackingLimit(f"An action can hold at most {MAX_EVENTS_PER_ACTION} entries.")
    current = ActionStatus(action.status)
    new = ActionStatus(fields["status"])
    occurred_on = fields.get("occurred_on")
    validate_event(
        current,
        new,
        occurred_on,
        today or datetime.utcnow().date(),
        [(ActionStatus(e.status), e.occurred_on) for e in events],
    )
    evidence = fields.get("evidence_sha256")
    if evidence:
        found = await db.execute(
            select(KadiCaseDocument.id).where(
                KadiCaseDocument.case_id == case_id, KadiCaseDocument.sha256 == evidence
            )
        )
        if found.first() is None:
            raise TrackingError("That document is not part of this case. Add it to the case first.")

    now = datetime.utcnow()
    changes: Dict[str, Any] = {"status": new.value, "updated_at": now}
    for name in ("institution", "next_step"):
        if fields.get(name) is not None:
            changes[name] = _clean(fields[name])
    for name in ("contact_method", "amount_disputed", "amount_corrected"):
        if fields.get(name) is not None:
            changes[name] = fields[name]
    # Conditional on the status just validated: a concurrent update cannot be overwritten.
    moved = await db.execute(
        update(KadiCaseAction)
        .where(KadiCaseAction.id == action_id, KadiCaseAction.status == current.value)
        .values(**changes)
        .execution_options(synchronize_session=False)
    )
    if moved.rowcount != 1:
        await db.rollback()
        raise ConcurrentUpdate("This action changed while you were editing it. Reload and try again.")
    event = KadiCaseActionEvent(
        id=f"EVT-{secrets.token_hex(10)}",
        action_id=action_id,
        case_id=case_id,
        sequence=events[-1].sequence + 1 if events else 1,
        status=new.value,
        occurred_on=occurred_on,
        note=_clean(fields.get("note")),
        evidence_sha256=evidence,
        provenance=PROVENANCE_USER,
        created_at=now,
    )
    db.add(event)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConcurrentUpdate("This action changed while you were editing it. Reload and try again.")
    await db.refresh(action)
    return view(action, await _events(db, action_id))


async def delete_action(db: AsyncSession, case_id: str, action_id: str) -> None:
    await _action(db, case_id, action_id)
    await db.execute(delete(KadiCaseActionEvent).where(KadiCaseActionEvent.action_id == action_id))
    await db.execute(delete(KadiCaseAction).where(KadiCaseAction.id == action_id))
    await db.commit()
    logger.info("Action %s removed from case %s.", action_id, case_id)
