"""
SchemeSetu — single source of truth for the income criteria the rule engine evaluates.

`agent.check_eligibility`, `reasoning_agent` and the consent-bounded recommendation
trigger (`triggers.py`, #92) all read these values; previously the numbers were duplicated
in two modules.

Provenance, stated plainly: both thresholds are project heuristics carried over from the
Phase-2 rule engine. They have **not** been verified against official NHA (PMJAY) or SHAS
Maharashtra (MJPJAY) guidelines, and the engine does not evaluate the other criteria those
schemes use (see `agent.UNEVALUATED_CRITERIA`). Every consumer surfaces `provenance`, and
every result stays provisional.
"""

from typing import FrozenSet, List, Literal, Optional

from pydantic import BaseModel

ThresholdProvenance = Literal["UNVERIFIED_PROJECT_HEURISTIC"]


class SchemeIncomeCriterion(BaseModel):
    scheme_name: str
    short_name: str
    max_annual_income_inr: float
    applicable_states: Optional[FrozenSet[str]] = None  # None: applies in every state
    provenance: ThresholdProvenance = "UNVERIFIED_PROJECT_HEURISTIC"
    note: str

    def applies_to_state(self, state: Optional[str]) -> bool:
        if self.applicable_states is None:
            return True
        return (state or "").strip().lower() in self.applicable_states

    def income_within(self, income: float) -> bool:
        return income <= self.max_annual_income_inr


PMJAY = SchemeIncomeCriterion(
    scheme_name="PMJAY (Ayushman Bharat)",
    short_name="PMJAY",
    max_annual_income_inr=250000,
    note=(
        "Project heuristic, not verified against NHA guidelines. The engine does not "
        "evaluate SECC-2011 deprivation status or ration-card criteria."
    ),
)

MJPJAY = SchemeIncomeCriterion(
    scheme_name="MJPJAY (Mahatma Jyotirao Phule Jan Arogya Yojana)",
    short_name="MJPJAY",
    max_annual_income_inr=150000,
    applicable_states=frozenset({"maharashtra", "mh"}),
    note="Project heuristic, not verified against SHAS Maharashtra guidelines.",
)

SCHEME_INCOME_CRITERIA: List[SchemeIncomeCriterion] = [PMJAY, MJPJAY]


def format_inr(amount: float) -> str:
    """Indian digit grouping: 250000 -> "2,50,000"."""
    digits = f"{int(round(amount))}"
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups + [tail])
