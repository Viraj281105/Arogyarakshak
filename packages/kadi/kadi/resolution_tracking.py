"""
Action and resolution tracking: the rules (ADR-031).

A finding is not an outcome. This module says which states a user's action can be in and
which moves between them are possible, so no screen can show "resolved" for something that
was only analysed, or "response received" for something never sent.

Every state here is the USER'S OWN RECORD of what happened. ArogyaRakshak sends nothing to a
hospital, insurer or authority and cannot confirm that anything was sent, received or
decided; there is therefore no "submitted" or "accepted" state.
"""

from datetime import date
from enum import Enum
from typing import Dict, FrozenSet, Iterable, Optional, Tuple


class ActionModule(str, Enum):
    BILLNYAY = "billnyay"
    BIMANYAY = "bimanyay"
    DAWACHECK = "dawacheck"
    DAAVISETU = "daavisetu"
    SCHEMESETU = "schemesetu"
    KADI = "kadi"


class ActionKind(str, Enum):
    CLARIFICATION_REQUEST = "clarification_request"
    APPEAL_OR_GRIEVANCE = "appeal_or_grievance"
    COLLECT_DOCUMENTS = "collect_documents"
    CONFIRM_WITH_DOCTOR = "confirm_with_doctor"
    ASK_PHARMACIST = "ask_pharmacist"
    CHECK_ELIGIBILITY = "check_eligibility"
    OTHER = "other"


class ContactMethod(str, Enum):
    IN_PERSON = "in_person"
    PHONE = "phone"
    EMAIL = "email"
    LETTER = "letter"
    ONLINE_PORTAL = "online_portal"
    OTHER = "other"


class ActionStatus(str, Enum):
    PLANNED = "planned"
    DRAFT_PREPARED = "draft_prepared"
    SENT = "sent"  # the user says they sent or raised it
    AWAITING_RESPONSE = "awaiting_response"
    RESPONSE_RECEIVED = "response_received"
    FURTHER_ACTION_NEEDED = "further_action_needed"
    RESOLVED = "resolved"  # the user says so
    PARTIALLY_RESOLVED = "partially_resolved"
    UNRESOLVED = "unresolved"
    CLOSED = "closed"  # closed without a resolution
    WITHDRAWN = "withdrawn"


_S = ActionStatus
_STOP = (_S.CLOSED, _S.WITHDRAWN)
_OUTCOMES = (_S.RESOLVED, _S.PARTIALLY_RESOLVED, _S.UNRESOLVED)


def _to(*statuses: ActionStatus) -> FrozenSet[ActionStatus]:
    return frozenset(statuses)


ALLOWED_TRANSITIONS: Dict[ActionStatus, FrozenSet[ActionStatus]] = {
    _S.PLANNED: _to(_S.DRAFT_PREPARED, _S.SENT, *_STOP),
    _S.DRAFT_PREPARED: _to(_S.SENT, _S.PLANNED, *_STOP),
    _S.SENT: _to(_S.AWAITING_RESPONSE, _S.RESPONSE_RECEIVED, _S.FURTHER_ACTION_NEEDED, *_OUTCOMES, *_STOP),
    _S.AWAITING_RESPONSE: _to(_S.RESPONSE_RECEIVED, _S.FURTHER_ACTION_NEEDED, *_OUTCOMES, *_STOP),
    _S.RESPONSE_RECEIVED: _to(_S.AWAITING_RESPONSE, _S.FURTHER_ACTION_NEEDED, *_OUTCOMES, *_STOP),
    _S.FURTHER_ACTION_NEEDED: _to(_S.DRAFT_PREPARED, _S.SENT, *_OUTCOMES, *_STOP),
    # An outcome can be reopened: things change after "resolved".
    _S.RESOLVED: _to(_S.FURTHER_ACTION_NEEDED),
    _S.PARTIALLY_RESOLVED: _to(_S.FURTHER_ACTION_NEEDED, _S.RESOLVED, _S.CLOSED),
    _S.UNRESOLVED: _to(_S.FURTHER_ACTION_NEEDED, _S.RESOLVED, _S.PARTIALLY_RESOLVED, _S.CLOSED),
    _S.CLOSED: _to(_S.FURTHER_ACTION_NEEDED),
    _S.WITHDRAWN: _to(_S.PLANNED),
}

# Moves that report something that happened in the world need the day it happened.
STATUSES_NEEDING_A_DATE: FrozenSet[ActionStatus] = frozenset({_S.SENT, _S.RESPONSE_RECEIVED})


class TrackingError(ValueError):
    """A record that cannot be true. The message is safe to show."""


class ImpossibleTransition(TrackingError):
    pass


def validate_event(
    current: ActionStatus,
    new: ActionStatus,
    occurred_on: Optional[date],
    today: date,
    history: Iterable[Tuple[ActionStatus, Optional[date]]] = (),
) -> None:
    """Raises TrackingError when moving from ``current`` to ``new`` on ``occurred_on`` cannot
    be a true record. ``history`` is the earlier (status, date) events of the same action."""
    if new not in ALLOWED_TRANSITIONS[current]:
        allowed = ", ".join(sorted(s.value for s in ALLOWED_TRANSITIONS[current]))
        raise ImpossibleTransition(f"An action that is '{current.value}' can only become: {allowed}.")
    if new in STATUSES_NEEDING_A_DATE and occurred_on is None:
        raise TrackingError("Say which day this happened.")
    if occurred_on is None:
        return
    # One day of slack: the server clock is UTC, the user's calendar may be a day ahead.
    if (occurred_on - today).days > 1:
        raise TrackingError("The date cannot be in the future.")
    if new == ActionStatus.RESPONSE_RECEIVED:
        sent_days = [day for status, day in history if status == ActionStatus.SENT and day]
        if sent_days and occurred_on < max(sent_days):
            raise TrackingError("A response cannot be dated before the day you sent it.")
