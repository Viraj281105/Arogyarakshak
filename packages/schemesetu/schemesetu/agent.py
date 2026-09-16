"""
SchemeSetu — Scheme Eligibility Agent.

Reports provisional eligibility for government healthcare schemes (PMJAY, MJPJAY) against the
cited official criteria in `schemesetu.thresholds`. Annual income is recorded and echoed back
but never decides a verdict: neither scheme defines an income ceiling in those sources.
"""

import logging
from typing import List
from pydantic import BaseModel, Field

from schemesetu.thresholds import MJPJAY, PMJAY, Citation, format_inr
from schemesetu.dialect_normalizer import normalize_state_name

logger = logging.getLogger("SchemeSetu.Agent")
logger.setLevel(logging.INFO)


class EligibilityRequest(BaseModel):
    income: float = Field(..., description="Annual family income in INR")
    location_state: str = Field(..., description="State of residence")
    category: str = Field("General", description="Social category (e.g. SC, ST, OBC, General)")
    medical_need: str = Field(..., description="Details of medical procedure or condition")


# Inputs the API accepts that influence no verdict. `category` and `medical_need` are not
# criteria of either scheme in the cited sources; income is recorded but has no official ceiling.
UNUSED_INPUTS = ["social_category", "medical_need"]
NON_DETERMINATIVE_FACTORS = ["annual_income"]


class SchemeResult(BaseModel):
    scheme_name: str
    estimated_eligibility: str = Field(..., description='"eligible" | "ineligible" | "ambiguous"')
    reason: str
    claim_guide_steps: List[str] = Field(
        ..., description="Next steps: how to claim when eligible, how to verify when ambiguous."
    )
    criteria_evaluated: List[str] = Field(
        ..., description="Criteria that actually decided this determination."
    )
    non_determinative_factors: List[str] = Field(
        default_factory=lambda: list(NON_DETERMINATIVE_FACTORS),
        description="Inputs recorded and reported but never used to decide: the cited official "
        "criteria define no annual income ceiling for either scheme.",
    )
    criteria_not_evaluated: List[str] = Field(
        ...,
        description="Eligibility factors this engine does not check. The result is "
        "provisional until these are verified against official records.",
    )
    is_provisional: bool = Field(
        True,
        description="Always true while unevaluated criteria remain. Callers must not "
        "present the result as a final eligibility decision.",
    )
    criteria_provenance: str = Field(..., description="Provenance of the criteria behind this result.")
    sources: List[Citation] = Field(..., description="Official sources for the criteria applied.")


def _income_note(income: float) -> str:
    return (
        f"Stated annual income (Rs {format_inr(income)}) is recorded but does not decide "
        "eligibility: the cited official criteria define no income ceiling."
    )


def check_eligibility(request: EligibilityRequest) -> List[SchemeResult]:
    """Check eligibility across PMJAY and MJPJAY based on intake data."""
    logger.info(f"[SchemeSetu] Assessing eligibility for state: {request.location_state}")
    income_note = _income_note(request.income)

    # MJPJAY's state check is an exact match against {"maharashtra", "mh"}. Without
    # normalization, a Devanagari ("महाराष्ट्र"), misspelled ("Maharastra"), or
    # city-name ("Mumbai") input silently fails the check with no explanation — MJPJAY
    # just does not appear, indistinguishable from genuinely not qualifying. See
    # dialect_normalizer.py for what this table does and does not cover.
    state_normalization = normalize_state_name(request.location_state)
    matching_state = state_normalization.normalized or request.location_state

    # PMJAY (national): eligibility rests on listing, occupation or age, none of which is
    # collected, so the verdict can only be "ambiguous" whatever the income.
    results = [
        SchemeResult(
            scheme_name=PMJAY.scheme_name,
            estimated_eligibility="ambiguous",
            reason=(
                f"AB PM-JAY eligibility is not income-based. {PMJAY.official_basis} None of these "
                f"facts is collected here, so eligibility cannot be determined. {income_note}"
            ),
            claim_guide_steps=list(PMJAY.verification_steps),
            criteria_evaluated=[],
            criteria_not_evaluated=PMJAY.criteria_not_evaluated + UNUSED_INPUTS,
            criteria_provenance=PMJAY.provenance,
            sources=PMJAY.citations,
        )
    ]

    # MJPJAY (Maharashtra): covers all families in the state, so stated residence decides.
    if MJPJAY.applies_to_state(matching_state):
        normalization_note = ""
        if state_normalization.was_normalized:
            normalization_note = (
                f' (interpreted "{state_normalization.original_input}" as Maharashtra'
                f" based on {'a known spelling/Devanagari variant' if state_normalization.normalization_basis == 'devanagari_or_spelling_variant' else 'the city name you entered'})"
            )
        results.append(
            SchemeResult(
                scheme_name=MJPJAY.scheme_name,
                estimated_eligibility="eligible",
                reason=(
                    f"Stated residence is Maharashtra{normalization_note}. {MJPJAY.official_basis} "
                    f"Residence was not verified against documents. {income_note}"
                ),
                claim_guide_steps=list(MJPJAY.verification_steps),
                criteria_evaluated=["state_of_residence"],
                criteria_not_evaluated=MJPJAY.criteria_not_evaluated + UNUSED_INPUTS,
                criteria_provenance=MJPJAY.provenance,
                sources=MJPJAY.citations,
            )
        )

    return results
