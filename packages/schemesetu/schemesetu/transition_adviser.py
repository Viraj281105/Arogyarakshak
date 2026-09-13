"""
SchemeSetu — Scheme-to-Scheme Transition Adviser (#71).

Generates a transition checklist when a patient's estimated eligibility changes between
PMJAY (national) and MJPJAY (Maharashtra state) — e.g. relocating into/out of
Maharashtra, or crossing an income threshold. Built entirely on the same eligibility
rules `schemesetu.agent.check_eligibility` already evaluates; it adds no new
eligibility criteria of its own; the checklist items are standard scheme-transfer
housekeeping steps (address/ration-card update, empanelment re-verification), not
scheme-specific legal advice.
"""

from typing import List, Set
from pydantic import BaseModel

from schemesetu.agent import EligibilityRequest, SchemeResult, check_eligibility

_PMJAY = "PMJAY (Ayushman Bharat)"
_MJPJAY = "MJPJAY (Mahatma Jyotirao Phule Jan Arogya Yojana)"


class TransitionAdvice(BaseModel):
    from_schemes: str
    to_schemes: str
    transition_detected: bool
    checklist: List[str]
    note: str


def _eligible_schemes(results: List[SchemeResult]) -> Set[str]:
    return {r.scheme_name for r in results if r.estimated_eligibility == "eligible"}


def advise_transition(previous: EligibilityRequest, current: EligibilityRequest) -> TransitionAdvice:
    """Compares eligibility under `previous` and `current` intake data and produces a
    transition checklist only when the set of eligible schemes actually changed."""
    previous_eligible = _eligible_schemes(check_eligibility(previous))
    current_eligible = _eligible_schemes(check_eligibility(current))

    gained = current_eligible - previous_eligible
    lost = previous_eligible - current_eligible
    from_label = "; ".join(sorted(previous_eligible)) or "None"
    to_label = "; ".join(sorted(current_eligible)) or "None"

    if not gained and not lost:
        return TransitionAdvice(
            from_schemes=from_label,
            to_schemes=to_label,
            transition_detected=False,
            checklist=[],
            note="No change in estimated scheme eligibility between the two intakes.",
        )

    checklist: List[str] = []
    if _MJPJAY in lost or _PMJAY in gained:
        checklist.extend(
            [
                "Update your address proof and ration card details with the relevant state authority.",
                "Retain your previous scheme's health card/records — hospitals may request continuity-of-care history.",
                "Re-verify eligibility at the nearest empanelled hospital's Ayushman/Arogya Mitra desk before your next admission.",
            ]
        )
    if _PMJAY in lost or _MJPJAY in gained:
        checklist.extend(
            [
                "Obtain the Maharashtra-specific health card (Orange/Yellow ration card linkage) required for MJPJAY.",
                "Confirm your hospital is empanelled under MJPJAY specifically — PMJAY and MJPJAY empanelment lists differ.",
            ]
        )
    if not checklist:
        checklist.append(
            "Eligibility has changed — consult the nearest empanelled hospital's help desk before your next claim."
        )

    return TransitionAdvice(
        from_schemes=from_label,
        to_schemes=to_label,
        transition_detected=True,
        checklist=checklist,
        note=(
            f"Gained eligibility: {', '.join(sorted(gained)) or 'none'}. "
            f"Lost eligibility: {', '.join(sorted(lost)) or 'none'}."
        ),
    )
