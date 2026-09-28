"""
Clinical statement and review lifecycle rules (ADR-011).

The rules live here, DB-agnostic, so the API layer cannot drift from them and they can
be unit-tested without a database.
"""

import hashlib
import json
import re
from typing import Any, Dict, Iterable, List, Optional

from .types import ReviewStatus, StatementStatus

# The reviewer must send this exact sentence to finalize. A boolean alone is too easy
# for a client (or a script driving one) to set by default; the sentence has to be
# deliberately supplied, and the server never supplies it on anyone's behalf.
FINALIZATION_CONFIRMATION_TEXT = (
    "I confirm that this statement represents my own professional judgment based on "
    "the information reviewed."
)

FACT_DECISION_CONFIRMATION_TEXT = (
    "I confirm that this decision represents my own professional judgment based on "
    "the information reviewed."
)

MAX_STATEMENT_CHARS = 8000
MAX_LIMITATIONS_CHARS = 3000
MAX_QUESTION_CHARS = 1000
MAX_DISCLOSURE_CHARS = 1000

EDITABLE_STATEMENT_STATES = frozenset({StatementStatus.DRAFT.value})
FINALIZABLE_STATEMENT_STATES = frozenset(
    {StatementStatus.DRAFT.value, StatementStatus.UNDER_REVIEW.value}
)
# Only these may ever be shown to the case holder or put into a package.
PUBLISHED_STATEMENT_STATES = frozenset(
    {StatementStatus.FINALIZED.value, StatementStatus.SUPERSEDED.value, StatementStatus.WITHDRAWN.value}
)
# Only this may be presented as a current opinion.
CURRENT_STATEMENT_STATES = frozenset({StatementStatus.FINALIZED.value})

OPEN_REVIEW_STATES = frozenset(
    {ReviewStatus.REQUESTED.value, ReviewStatus.ASSIGNED.value, ReviewStatus.IN_REVIEW.value}
)
ASSIGNABLE_REVIEW_STATES = frozenset({ReviewStatus.REQUESTED.value, ReviewStatus.DECLINED.value})

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class LifecycleError(ValueError):
    """A requested transition is not allowed. The message is safe to show to callers."""


def clean_text(value: Optional[str], *, max_chars: int, field: str, required: bool = True) -> Optional[str]:
    """Strips control characters and bounds length. Human-entered text is stored as
    literal text and escaped at every render site; this only removes bytes that have
    no business in a clinical statement."""
    if value is None:
        if required:
            raise LifecycleError(f"{field} is required.")
        return None
    cleaned = _CONTROL_CHARS.sub("", value).strip()
    if required and not cleaned:
        raise LifecycleError(f"{field} must not be empty.")
    if len(cleaned) > max_chars:
        raise LifecycleError(f"{field} exceeds {max_chars} characters.")
    return cleaned or None


def require_confirmation(confirmation: bool, confirmation_text: Optional[str], expected: str) -> None:
    if confirmation is not True:
        raise LifecycleError("Explicit reviewer confirmation is required.")
    if (confirmation_text or "").strip() != expected:
        raise LifecycleError(
            "The confirmation sentence must be supplied exactly as shown: " + expected
        )


def ensure_editable(status: str) -> None:
    if status not in EDITABLE_STATEMENT_STATES:
        raise LifecycleError(
            f"A statement in state {status} cannot be edited. Finalized statements are "
            "immutable; create a new version with 'revise' instead."
        )


def ensure_submittable(status: str) -> None:
    if status != StatementStatus.DRAFT.value:
        raise LifecycleError(f"Only a DRAFT statement can be submitted (current: {status}).")


def ensure_finalizable(status: str) -> None:
    if status not in FINALIZABLE_STATEMENT_STATES:
        raise LifecycleError(f"A statement in state {status} cannot be finalized.")


def ensure_revisable(status: str) -> None:
    if status != StatementStatus.FINALIZED.value:
        raise LifecycleError(
            f"Only the current FINALIZED statement can be revised (current: {status})."
        )


def ensure_withdrawable(status: str) -> None:
    if status != StatementStatus.FINALIZED.value:
        raise LifecycleError(f"Only a FINALIZED statement can be withdrawn (current: {status}).")


def statement_content_hash(fields: Dict[str, Any]) -> str:
    """SHA-256 over the canonical JSON of a finalized statement's content — stored at
    finalization so any later alteration of the row is detectable."""
    canonical = json.dumps(fields, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def hashed_statement_fields(
    *,
    statement_id: str,
    review_id: str,
    case_id: str,
    reviewer_id: str,
    version: int,
    clinical_question: str,
    evidence_reviewed: Iterable[Any],
    reviewer_statement: str,
    limitations: str,
    coi_category: str,
    coi_disclosure: Optional[str],
    reviewer_snapshot: Dict[str, Any],
    confirmation_text: str,
) -> Dict[str, Any]:
    return {
        "statement_id": statement_id,
        "review_id": review_id,
        "case_id": case_id,
        "reviewer_id": reviewer_id,
        "version": version,
        "clinical_question": clinical_question,
        "evidence_reviewed": list(evidence_reviewed),
        "reviewer_statement": reviewer_statement,
        "limitations": limitations,
        "coi_category": coi_category,
        "coi_disclosure": coi_disclosure,
        "reviewer_snapshot": reviewer_snapshot,
        "confirmation_text": confirmation_text,
    }


def validate_evidence_selection(selected: List[str], available: Iterable[str]) -> List[str]:
    """A reviewer may only cite evidence items that were actually shared with them."""
    available_set = set(available)
    unknown = [item for item in selected if item not in available_set]
    if unknown:
        raise LifecycleError(
            "evidence_reviewed may only reference items in this review's evidence packet; "
            f"unknown: {', '.join(sorted(unknown)[:5])}"
        )
    if not selected:
        raise LifecycleError("evidence_reviewed must list at least one evidence item you reviewed.")
    # Preserve order, drop duplicates.
    return list(dict.fromkeys(selected))
