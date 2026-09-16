"""
SchemeSetu — consent-bounded scheme recommendation trigger (#92).

Decides whether a case's saved income profile should trigger a background eligibility
run. The decision is deterministic and deliberately conservative:

- no saved profile              -> INSUFFICIENT_EVIDENCE (eligibility is never assumed)
- a scheme applies that did not
  apply to the previous profile -> FIRE (first profile, or a state change made a state
                                   scheme applicable)
- the same schemes apply as for
  the previous profile          -> NO_CHANGE (nothing new to recommend)

Income never fires a run on its own. Neither scheme defines an annual income ceiling in the
official sources cited in `thresholds.py`, so income is non-determinative: an income change
cannot change any verdict. Which schemes apply depends only on the state of residence.

The consent boundary is enforced by the caller (apps/api): a profile can only be saved,
and a run can only fire, for a case whose stored `consent_opt_in` is true.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from schemesetu.thresholds import SCHEME_CRITERIA, IncomeRole, SchemeCriteria

TriggerStatus = Literal["FIRE", "NO_CHANGE", "INSUFFICIENT_EVIDENCE"]


class IncomeProfile(BaseModel):
    annual_income_inr: float = Field(..., ge=0, le=1e10, allow_inf_nan=False)
    state: str = Field(..., min_length=2, max_length=64)


class SchemeMatch(BaseModel):
    scheme_name: str
    short_name: str
    provenance: str


class IncomeTriggerDecision(BaseModel):
    status: TriggerStatus
    schemes_applicable: List[SchemeMatch] = Field(default_factory=list)
    newly_applicable: List[SchemeMatch] = Field(default_factory=list)
    reason: str
    income_role: IncomeRole = "NON_DETERMINATIVE"


def _match(criteria: SchemeCriteria) -> SchemeMatch:
    return SchemeMatch(
        scheme_name=criteria.scheme_name,
        short_name=criteria.short_name,
        provenance=criteria.provenance,
    )


def applicable_schemes(profile: IncomeProfile) -> List[SchemeCriteria]:
    return [c for c in SCHEME_CRITERIA if c.applies_to_state(profile.state)]


def evaluate_income_trigger(
    current: Optional[IncomeProfile], previous: Optional[IncomeProfile] = None
) -> IncomeTriggerDecision:
    if current is None:
        return IncomeTriggerDecision(
            status="INSUFFICIENT_EVIDENCE",
            reason="No income profile is saved for this case; eligibility is never assumed.",
        )

    applicable = applicable_schemes(current)
    before = {c.short_name for c in applicable_schemes(previous)} if previous else set()
    newly = [c for c in applicable if c.short_name not in before]

    if not newly:
        return IncomeTriggerDecision(
            status="NO_CHANGE",
            schemes_applicable=[_match(c) for c in applicable],
            reason=(
                "The same schemes apply as for the previously saved profile. Income changes alone "
                "never trigger a run: no evaluated scheme defines an income ceiling."
            ),
        )
    return IncomeTriggerDecision(
        status="FIRE",
        schemes_applicable=[_match(c) for c in applicable],
        newly_applicable=[_match(c) for c in newly],
        reason="Newly applicable for this state of residence: " + ", ".join(c.short_name for c in newly) + ".",
    )
