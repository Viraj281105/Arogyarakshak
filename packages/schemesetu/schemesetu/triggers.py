"""
SchemeSetu — consent-bounded scheme recommendation trigger (#92).

Decides whether a case's saved income profile should trigger a background eligibility
run. The decision is deterministic and deliberately conservative:

- no saved profile              -> INSUFFICIENT_EVIDENCE (eligibility is never assumed)
- income above every applicable
  scheme threshold              -> NO_THRESHOLD_CROSSED
- within a threshold it was not
  already within last time      -> FIRE (first profile, income dropped below a threshold,
                                   or a state change made a state scheme applicable)
- within the same thresholds as
  the previous profile          -> NO_THRESHOLD_CROSSED (nothing new to recommend)

The consent boundary is enforced by the caller (apps/api): a profile can only be saved,
and a run can only fire, for a case whose stored `consent_opt_in` is true. Thresholds come
from `thresholds.py` and are unverified project heuristics; that provenance travels with
every decision.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from schemesetu.thresholds import SCHEME_INCOME_CRITERIA, SchemeIncomeCriterion

TriggerStatus = Literal["FIRE", "NO_THRESHOLD_CROSSED", "INSUFFICIENT_EVIDENCE"]


class IncomeProfile(BaseModel):
    annual_income_inr: float = Field(..., ge=0, le=1e10, allow_inf_nan=False)
    state: str = Field(..., min_length=2, max_length=64)


class ThresholdMatch(BaseModel):
    scheme_name: str
    short_name: str
    max_annual_income_inr: float
    provenance: str


class IncomeTriggerDecision(BaseModel):
    status: TriggerStatus
    schemes_within_threshold: List[ThresholdMatch] = Field(default_factory=list)
    newly_within_threshold: List[ThresholdMatch] = Field(default_factory=list)
    reason: str
    threshold_provenance: str = "UNVERIFIED_PROJECT_HEURISTIC"


def _match(criterion: SchemeIncomeCriterion) -> ThresholdMatch:
    return ThresholdMatch(
        scheme_name=criterion.scheme_name,
        short_name=criterion.short_name,
        max_annual_income_inr=criterion.max_annual_income_inr,
        provenance=criterion.provenance,
    )


def schemes_within_threshold(profile: IncomeProfile) -> List[SchemeIncomeCriterion]:
    return [
        c
        for c in SCHEME_INCOME_CRITERIA
        if c.applies_to_state(profile.state) and c.income_within(profile.annual_income_inr)
    ]


def evaluate_income_trigger(
    current: Optional[IncomeProfile], previous: Optional[IncomeProfile] = None
) -> IncomeTriggerDecision:
    if current is None:
        return IncomeTriggerDecision(
            status="INSUFFICIENT_EVIDENCE",
            reason="No income profile is saved for this case; eligibility is never assumed.",
        )

    within = schemes_within_threshold(current)
    before = {c.short_name for c in schemes_within_threshold(previous)} if previous else set()
    newly = [c for c in within if c.short_name not in before]

    if not within:
        return IncomeTriggerDecision(
            status="NO_THRESHOLD_CROSSED",
            reason="Income is above every evaluated scheme income threshold for this state.",
        )
    if not newly:
        return IncomeTriggerDecision(
            status="NO_THRESHOLD_CROSSED",
            schemes_within_threshold=[_match(c) for c in within],
            reason="Income is within the same scheme thresholds as the previously saved profile.",
        )
    return IncomeTriggerDecision(
        status="FIRE",
        schemes_within_threshold=[_match(c) for c in within],
        newly_within_threshold=[_match(c) for c in newly],
        reason="Income is within the income threshold of: " + ", ".join(c.short_name for c in newly) + ".",
    )
