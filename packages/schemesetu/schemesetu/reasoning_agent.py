"""
SchemeSetu — Eligibility Reasoning Agent (#21).

Produces an explainable, step-by-step reasoning trace for a PMJAY/MJPJAY eligibility
determination, walking a structured criteria index instead of returning an opaque verdict.

Architectural note: this is NOT retrieval-augmented generation over a vector index.
ArogyaRakshak's vector-search scaffold (`packages/kadi/kadi/vector_store.py`) is
unwired — no embeddings are computed and no similarity search runs anywhere in this
codebase (see `docs/architecture/components.md`, marked "planned — not implemented").
The "index" here is a small, explicit Python structure covering the same PMJAY/MJPJAY
criteria `schemesetu.agent.check_eligibility` already evaluates — a lookup table, not a
learned representation — so this agent can be explainable without pretending a
retrieval system exists where none does.
"""

from typing import Any, Callable, List
from pydantic import BaseModel, Field

from schemesetu.agent import (
    EligibilityRequest,
    EVALUATED_CRITERIA,
    UNEVALUATED_CRITERIA,
    SchemeResult,
    check_eligibility,
)


class ReasoningStep(BaseModel):
    criterion: str
    scheme: str
    threshold_or_rule: str
    applicant_value: str
    satisfied: bool


class EligibilityReasoning(BaseModel):
    scheme_results: List[SchemeResult]
    reasoning_trace: List[ReasoningStep]
    criteria_considered: List[str]
    criteria_not_considered: List[str] = Field(
        default_factory=lambda: list(UNEVALUATED_CRITERIA),
        description="Same disclosure as SchemeResult — factors this reasoning agent "
        "does not check, so the trace above is not mistaken for exhaustive.",
    )


def _income_rule(threshold: float) -> Callable[[EligibilityRequest], bool]:
    return lambda req: req.income <= threshold


def _is_maharashtra(req: EligibilityRequest) -> bool:
    return req.location_state.lower() in ["maharashtra", "mh"]


# The structured criteria index this agent reasons over — the same rules
# schemesetu.agent.check_eligibility applies, made explicit and inspectable here
# instead of staying buried inside branching if/else logic.
_PMJAY = "PMJAY (Ayushman Bharat)"
_MJPJAY = "MJPJAY (Mahatma Jyotirao Phule Jan Arogya Yojana)"

_CRITERIA_INDEX: List[dict] = [
    {
        "scheme": _PMJAY,
        "criterion": "annual_income",
        "rule": "Annual family income <= Rs 2,50,000",
        "check": _income_rule(250000),
        "applies": lambda req: True,
    },
    {
        "scheme": _MJPJAY,
        "criterion": "state_of_residence",
        "rule": "Resident of Maharashtra",
        "check": _is_maharashtra,
        "applies": lambda req: True,
    },
    {
        "scheme": _MJPJAY,
        "criterion": "annual_income",
        "rule": "Annual family income <= Rs 1,50,000",
        "check": _income_rule(150000),
        # MJPJAY's income criterion is only meaningful for Maharashtra residents —
        # schemesetu.agent never evaluates it otherwise.
        "applies": _is_maharashtra,
    },
]


def reason_about_eligibility(request: EligibilityRequest) -> EligibilityReasoning:
    """Runs the same eligibility rules as `check_eligibility`, and additionally
    returns a step-by-step trace of which criteria were checked, against what
    threshold, and whether the applicant satisfied each one."""
    scheme_results = check_eligibility(request)

    trace: List[ReasoningStep] = []
    for entry in _CRITERIA_INDEX:
        if not entry["applies"](request):
            continue
        applicant_value = (
            f"Rs {request.income:,.0f}"
            if entry["criterion"] == "annual_income"
            else request.location_state
        )
        trace.append(
            ReasoningStep(
                criterion=entry["criterion"],
                scheme=entry["scheme"],
                threshold_or_rule=entry["rule"],
                applicant_value=applicant_value,
                satisfied=bool(entry["check"](request)),
            )
        )

    return EligibilityReasoning(
        scheme_results=scheme_results,
        reasoning_trace=trace,
        criteria_considered=list(EVALUATED_CRITERIA),
        criteria_not_considered=list(UNEVALUATED_CRITERIA),
    )
