"""
Append-only clinical audit trail (ADR-011).

`details` is sanitised structurally: only booleans, numbers, None, and SHORT strings
(ids, statuses, enum values) survive, plus short lists of those. Anything longer — a
statement, an evidence value, a document excerpt — is dropped, so a careless call site
cannot write patient-sensitive content into the audit log.
"""

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KadiClinicalAuditEvent

MAX_DETAIL_STRING = 80
MAX_DETAIL_LIST = 20


def _safe_scalar(value: Any) -> bool:
    if value is None or isinstance(value, (bool, int, float)):
        return True
    return isinstance(value, str) and len(value) <= MAX_DETAIL_STRING


def sanitize_details(details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    clean: Dict[str, Any] = {}
    for key, value in (details or {}).items():
        if not isinstance(key, str) or len(key) > 40:
            continue
        if _safe_scalar(value):
            clean[key] = value
        elif isinstance(value, (list, tuple)) and len(value) <= MAX_DETAIL_LIST and all(
            _safe_scalar(v) for v in value
        ):
            clean[key] = list(value)
    return clean


def record_event(
    db: AsyncSession,
    *,
    event_type: str,
    subject_type: str,
    subject_id: str,
    actor_type: str,
    actor_id: Optional[str] = None,
    case_id: Optional[str] = None,
    review_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> KadiClinicalAuditEvent:
    event = KadiClinicalAuditEvent(
        id=f"AUD-{uuid.uuid4().hex[:12]}",
        case_id=case_id,
        review_id=review_id,
        subject_type=subject_type,
        subject_id=subject_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        details=sanitize_details(details),
    )
    db.add(event)
    return event


def event_view(event: KadiClinicalAuditEvent) -> Dict[str, Any]:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "subject_type": event.subject_type,
        "subject_id": event.subject_id,
        "actor_type": event.actor_type,
        "actor_id": event.actor_id,
        "details": event.details or {},
        "created_at": event.created_at,
    }


async def events_for_review(db: AsyncSession, review_id: str) -> List[Dict[str, Any]]:
    rows = await db.execute(
        select(KadiClinicalAuditEvent)
        .where(KadiClinicalAuditEvent.review_id == review_id)
        .order_by(KadiClinicalAuditEvent.created_at, KadiClinicalAuditEvent.id)
    )
    return [event_view(e) for e in rows.scalars().all()]


async def events_for_subject(db: AsyncSession, subject_id: str) -> List[Dict[str, Any]]:
    rows = await db.execute(
        select(KadiClinicalAuditEvent)
        .where(KadiClinicalAuditEvent.subject_id == subject_id)
        .order_by(KadiClinicalAuditEvent.created_at, KadiClinicalAuditEvent.id)
    )
    return [event_view(e) for e in rows.scalars().all()]
