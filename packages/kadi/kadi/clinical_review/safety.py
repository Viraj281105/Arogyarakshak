"""
Clinical safety governance: red-flag escalation rules (ADR-011).

Doctors are not asked to invent a safety system. Each rule adapts a published protocol
(its source, version and section travel with the rule) to ArogyaRakshak's administrative
context, and becomes ACTIVE only after attributable approval by named review-board
members. Active rules are immutable; changes create a new version.

Honest limits, stated wherever rules are shown:
- Triggers are keyword matches over extracted case text. They do not understand
  negation ("no seizures") or context, so they over-escalate by design.
- The set of rules is a floor, never a claim of comprehensive coverage.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .types import SAFETY_FLOOR_DISCLAIMER


class RuleStatus(str, Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"


class RuleActionType(str, Enum):
    # Tell the user to seek clinical care now, before continuing any admin workflow.
    SHOW_SAFETY_ESCALATION = "SHOW_SAFETY_ESCALATION"
    # Recommend routing the case to a human clinical reviewer.
    RECOMMEND_CLINICAL_REVIEW = "RECOMMEND_CLINICAL_REVIEW"


class RuleSeverity(str, Enum):
    URGENT = "URGENT"
    ADVISORY = "ADVISORY"


EDITABLE_RULE_STATES = frozenset({RuleStatus.DRAFT.value})
IMMUTABLE_RULE_STATES = frozenset(
    {RuleStatus.APPROVED.value, RuleStatus.ACTIVE.value, RuleStatus.SUPERSEDED.value, RuleStatus.RETIRED.value}
)

TRIGGERABLE_CONTEXT_TYPES = frozenset({"document_text", "diagnosis", "procedure", "medicine"})
MAX_TERMS = 40
MIN_TERM_CHARS = 3
MAX_TERM_CHARS = 60
MAX_MESSAGE_CHARS = 500

NEGATION_LIMITATION = (
    "Keyword trigger: does not understand negation or context (e.g. 'no seizures' still "
    "matches 'seizure'), so it may escalate when it is not needed."
)


class RuleValidationError(ValueError):
    pass


def validate_trigger(trigger: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(trigger, dict):
        raise RuleValidationError("trigger must be an object.")
    terms = trigger.get("match_any")
    if not isinstance(terms, list) or not terms:
        raise RuleValidationError("trigger.match_any must be a non-empty list of terms.")
    if len(terms) > MAX_TERMS:
        raise RuleValidationError(f"trigger.match_any may contain at most {MAX_TERMS} terms.")
    clean_terms: List[str] = []
    for term in terms:
        if not isinstance(term, str):
            raise RuleValidationError("Every trigger term must be a string.")
        t = " ".join(term.split()).strip()
        if not (MIN_TERM_CHARS <= len(t) <= MAX_TERM_CHARS):
            raise RuleValidationError(
                f"Trigger term '{t[:20]}' must be {MIN_TERM_CHARS}-{MAX_TERM_CHARS} characters."
            )
        clean_terms.append(t)

    types = trigger.get("context_types") or ["document_text", "diagnosis"]
    if not isinstance(types, list) or any(t not in TRIGGERABLE_CONTEXT_TYPES for t in types):
        raise RuleValidationError(
            f"trigger.context_types must be a subset of {sorted(TRIGGERABLE_CONTEXT_TYPES)}."
        )
    return {"match_any": list(dict.fromkeys(clean_terms)), "context_types": list(dict.fromkeys(types))}


def validate_action(action: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(action, dict):
        raise RuleValidationError("action must be an object.")
    try:
        action_type = RuleActionType(action.get("type")).value
        severity = RuleSeverity(action.get("severity", RuleSeverity.ADVISORY.value)).value
    except ValueError as e:
        raise RuleValidationError(str(e)) from None
    message = action.get("message")
    if not isinstance(message, str) or not message.strip():
        raise RuleValidationError("action.message is required.")
    if len(message) > MAX_MESSAGE_CHARS:
        raise RuleValidationError(f"action.message exceeds {MAX_MESSAGE_CHARS} characters.")
    return {"type": action_type, "severity": severity, "message": message.strip()}


def rule_content_hash(fields: Dict[str, Any]) -> str:
    canonical = json.dumps(fields, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def ensure_rule_transition(current: str, target: str) -> None:
    allowed = {
        RuleStatus.DRAFT.value: {RuleStatus.UNDER_REVIEW.value},
        RuleStatus.UNDER_REVIEW.value: {RuleStatus.APPROVED.value, RuleStatus.DRAFT.value},
        RuleStatus.APPROVED.value: {RuleStatus.ACTIVE.value},
        RuleStatus.ACTIVE.value: {RuleStatus.SUPERSEDED.value, RuleStatus.RETIRED.value},
    }
    if target not in allowed.get(current, set()):
        raise RuleValidationError(f"A rule cannot move from {current} to {target}.")


def approvals_satisfied(approver_ids: Iterable[str], proposer_id: str, required: int) -> bool:
    """Four-eyes: the proposer's own approval never counts toward activation."""
    independent = {a for a in approver_ids if a != proposer_id}
    return len(independent) >= max(required, 1)


@dataclass(frozen=True)
class ActiveRule:
    rule_id: str
    rule_key: str
    version: int
    title: str
    trigger: Dict[str, Any]
    action: Dict[str, Any]
    source_name: str
    source_version: Optional[str]
    source_section: Optional[str]
    limitations: str
    effective_date: Optional[date]
    review_due_date: Optional[date]


def _term_pattern(term: str) -> "re.Pattern[str]":
    escaped = r"\s+".join(re.escape(part) for part in term.split())
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)


def evaluate_rules(
    rules: Sequence[ActiveRule],
    context: Sequence[Tuple[str, str]],
    today: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Returns one escalation per ACTIVE rule whose trigger matches the case context.

    `context` is (entity_type, text) pairs. Only the matched TERMS are returned — never
    the surrounding patient text — so an escalation can be logged or displayed without
    re-exposing the document.
    """
    today = today or date.today()
    escalations: List[Dict[str, Any]] = []
    for rule in rules:
        if rule.effective_date and rule.effective_date > today:
            continue
        types = set(rule.trigger.get("context_types") or [])
        texts = [text for (etype, text) in context if etype in types and text]
        if not texts:
            continue
        matched: List[str] = []
        for term in rule.trigger.get("match_any", []):
            pattern = _term_pattern(term)
            if any(pattern.search(text) for text in texts):
                matched.append(term)
        if not matched:
            continue
        escalations.append(escalation_for(rule, matched, today))
    return sort_escalations(escalations)


def sort_escalations(escalations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(escalations, key=lambda e: (0 if e["severity"] == RuleSeverity.URGENT.value else 1, e["title"]))


def escalation_for(rule: ActiveRule, matched_terms: Sequence[str], today: Optional[date] = None) -> Dict[str, Any]:
    today = today or date.today()
    return {
        "rule_id": rule.rule_id,
        "rule_key": rule.rule_key,
        "rule_version": rule.version,
        "title": rule.title,
        "action_type": rule.action["type"],
        "severity": rule.action["severity"],
        "message": rule.action["message"],
        "matched_terms": list(dict.fromkeys(matched_terms)),
        "source": {
            "name": rule.source_name,
            "version": rule.source_version,
            "section": rule.source_section,
        },
        "limitations": [rule.limitations, NEGATION_LIMITATION],
        "rule_review_overdue": bool(rule.review_due_date and rule.review_due_date < today),
        "human_review_recommended": True,
        "disclaimer": SAFETY_FLOOR_DISCLAIMER,
        "provenance": "AI_DERIVED",
    }


def carried_forward_terms(successor: ActiveRule, stored_terms: Sequence[str]) -> List[str]:
    """Terms an earlier version of a rule matched in a document's full text that the
    ACTIVE successor version still triggers on (over document text).

    A new version gets a new rule id; without this, a red flag found beyond the stored
    excerpt would silently disappear the moment the rule was re-versioned. Only terms
    the successor still lists carry forward — a term the board removed does not."""
    if "document_text" not in (successor.trigger.get("context_types") or []):
        return []
    def key(term: str) -> str:
        return " ".join((term or "").split()).casefold()

    current = {key(t) for t in successor.trigger.get("match_any", [])}
    return [t for t in stored_terms if key(t) in current]


def scan_full_text(rules: Sequence[ActiveRule], full_text: str, today: Optional[date] = None) -> List[Dict[str, Any]]:
    """Runs ACTIVE rules over a whole document while it is still in transient memory.

    Returns only (rule id, version, matched terms) — never any document text — so the
    result can be persisted without retaining the document (ADR-003)."""
    matches = evaluate_rules(rules, [("document_text", full_text)], today=today)
    return [
        {"rule_id": m["rule_id"], "rule_version": m["rule_version"], "matched_terms": m["matched_terms"]}
        for m in matches
    ]
