"""BimaNyay's reversal percentage must disclose that it is a heuristic prior (#90 context)."""

from bimanyay import ClaimDenialInput, analyze_insurance_denial
from bimanyay.models import DisputeAuditResult


def test_reversal_score_is_labelled_as_a_heuristic_prior():
    result = analyze_insurance_denial(
        ClaimDenialInput(
            policy_number="POL-TEST",
            insurer_name="Test Insurer",
            policy_age_years=6,
            claimed_amount=100000,
            denied_or_deducted_amount=100000,
            denial_category="PED_NON_DISCLOSURE",
            denial_reason_raw="Pre-existing disease not disclosed",
            diagnosis="Type 2 diabetes mellitus",
        ),
        language="en",
    )
    assert result.probability_basis == "HEURISTIC_PRIOR_NOT_HISTORICAL"
    schema = DisputeAuditResult.model_json_schema()
    assert "NOT derived from historical dispute outcomes" in schema["properties"]["reversal_probability_score"]["description"]
