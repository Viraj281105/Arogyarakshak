"""
SchemeSetu — Eligibility Reasoning Agent (#21).

Produces an explainable, step-by-step reasoning trace for a PMJAY/MJPJAY eligibility
determination, walking a structured criteria index instead of returning an opaque verdict.

Architectural note: this is NOT retrieval-augmented generation over a vector index.
ArogyaRakshak's vector-search scaffold (`packages/kadi/kadi/vector_store.py`) is
unwired — no embeddings are computed and no similarity search runs anywhere in this
codebase (see `docs/architecture/components.md`, marked "planned — not implemented").
The "index" here is a small, explicit Python structure covering the same PMJAY/MJPJAY
criteria `schemesetu.agent.check_eligibility` already applies — a lookup table, not a
learned representation — so this agent can be explainable without pretending a
retrieval system exists where none does.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from schemesetu.agent import EligibilityRequest, SchemeResult, check_eligibility
from schemesetu.thresholds import MJPJAY, PMJAY, format_inr


class ReasoningStep(BaseModel):
    criterion: str
    scheme: str
    threshold_or_rule: str
    applicant_value: str
    determinative: bool = Field(..., description="Whether this criterion can decide the verdict.")
    satisfied: Optional[bool] = Field(
        ...,
        description="None when the criterion is non-determinative or its input is not collected.",
    )


class EligibilityReasoning(BaseModel):
    scheme_results: List[SchemeResult]
    reasoning_trace: List[ReasoningStep]
    criteria_considered: List[str] = Field(
        ..., description="Determinative criteria this trace actually checked."
    )
    non_determinative_factors: List[str] = Field(
        ..., description="Inputs shown in the trace that cannot change a verdict."
    )
    criteria_not_considered: List[str] = Field(
        ...,
        description="Same disclosure as SchemeResult — factors this reasoning agent "
        "does not check, so the trace above is not mistaken for exhaustive.",
    )


def _is_maharashtra(req: EligibilityRequest) -> bool:
    return MJPJAY.applies_to_state(req.location_state)


def _income(req: EligibilityRequest) -> str:
    return f"Rs {format_inr(req.income)}"


_NO_INCOME_CEILING = "No income ceiling in the cited official criteria; recorded, not used to decide"

# The structured criteria index this agent reasons over — the same rules
# schemesetu.agent.check_eligibility applies, made explicit and inspectable here
# instead of staying buried inside branching logic. `check` returns None when the
# criterion cannot be evaluated from the intake.
_CRITERIA_INDEX: List[dict] = [
    {
        "scheme": PMJAY.scheme_name,
        "criterion": "beneficiary_identification",
        "rule": PMJAY.official_basis,
        "determinative": True,
        "value": lambda req: "not collected",
        "check": lambda req: None,
        "applies": lambda req: True,
    },
    {
        "scheme": PMJAY.scheme_name,
        "criterion": "annual_income",
        "rule": _NO_INCOME_CEILING,
        "determinative": False,
        "value": _income,
        "check": lambda req: None,
        "applies": lambda req: True,
    },
    {
        "scheme": MJPJAY.scheme_name,
        "criterion": "state_of_residence",
        "rule": f"Resident of Maharashtra. {MJPJAY.official_basis}",
        "determinative": True,
        "value": lambda req: req.location_state,
        "check": _is_maharashtra,
        "applies": lambda req: True,
    },
    {
        "scheme": MJPJAY.scheme_name,
        "criterion": "annual_income",
        "rule": _NO_INCOME_CEILING,
        "determinative": False,
        "value": _income,
        "check": lambda req: None,
        # schemesetu.agent only assesses MJPJAY for Maharashtra residents.
        "applies": _is_maharashtra,
    },
]


def reason_about_eligibility(request: EligibilityRequest) -> EligibilityReasoning:
    """Runs the same eligibility rules as `check_eligibility`, and additionally
    returns a step-by-step trace of which criteria were checked, against what
    rule, and whether the applicant satisfied each one."""
    scheme_results = check_eligibility(request)

    trace: List[ReasoningStep] = [
        ReasoningStep(
            criterion=entry["criterion"],
            scheme=entry["scheme"],
            threshold_or_rule=entry["rule"],
            applicant_value=entry["value"](request),
            determinative=entry["determinative"],
            satisfied=entry["check"](request),
        )
        for entry in _CRITERIA_INDEX
        if entry["applies"](request)
    ]

    return EligibilityReasoning(
        scheme_results=scheme_results,
        reasoning_trace=trace,
        criteria_considered=list(
            dict.fromkeys(s.criterion for s in trace if s.determinative and s.satisfied is not None)
        ),
        non_determinative_factors=list(dict.fromkeys(s.criterion for s in trace if not s.determinative)),
        criteria_not_considered=list(
            dict.fromkeys(c for r in scheme_results for c in r.criteria_not_evaluated)
        ),
    )
