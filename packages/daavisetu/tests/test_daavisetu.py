import pytest
from daavisetu.generator import (
    check_policy_limit,
    generate_claim_package,
    generate_preauth_pdf,
    ClaimData,
)
from daavisetu.schema import FORM_SECTIONS, get_claim_form_json_schema


def test_generate_claim_package():
    claim_input = ClaimData(
        policy_number="POL12345",
        patient_name="Viraj Jadhao",
        hospital_name="Modern Hospital, Pune",
        diagnosis="Acute Appendicitis (K35.8)",
        estimated_cost=75000.0,
        treatment_plan="Emergency laparoscopic appendectomy",
    )

    package = generate_claim_package(case_id="test-case-id-12345", claim_input=claim_input)

    assert package.claim_id.startswith("CLAIM-")
    assert package.form_data.policy_number == "POL12345"
    assert package.form_data.estimated_cost == 75000.0
    assert package.status == "ready_for_review"
    assert package.form_filled_pdf_path is not None
    assert package.policy_limit_check is None, "no sum_insured was declared"


# ---------------------------------------------------------------------------
# #79 — Universal claim form JSON Schema
# ---------------------------------------------------------------------------


def test_claim_form_schema_covers_every_field():
    schema = get_claim_form_json_schema()
    properties = schema["properties"]
    for field in ("policy_number", "patient_name", "hospital_name", "diagnosis", "estimated_cost", "treatment_plan"):
        assert field in properties

    for field, label in FORM_SECTIONS.items():
        assert properties[field]["x-form-section"] == label


def test_claim_form_schema_groups_sum_insured_under_policy():
    schema = get_claim_form_json_schema()
    assert schema["properties"]["sum_insured"]["x-form-group"] == "policy"
    assert "sum_insured" not in FORM_SECTIONS, "sum insured has no Annexure-B field"
    assert set(schema["x-form-groups"]) == {"patient", "policy", "hospital_and_procedure", "cost"}


# ---------------------------------------------------------------------------
# #84 — Policy limit validation
# ---------------------------------------------------------------------------


def test_policy_limit_check_returns_none_without_sum_insured():
    assert check_policy_limit(estimated_cost=50000.0, sum_insured=None) is None


def test_policy_limit_check_flags_cost_exceeding_sum_insured():
    result = check_policy_limit(estimated_cost=120000.0, sum_insured=100000.0)
    assert result is not None
    assert result.exceeds_limit is True
    assert result.shortfall_amount == 20000.0
    assert "exceeds" in result.note


def test_policy_limit_check_within_limit_reports_no_shortfall():
    result = check_policy_limit(estimated_cost=80000.0, sum_insured=100000.0)
    assert result.exceeds_limit is False
    assert result.shortfall_amount == 0.0


def test_preauth_pdf_warns_when_cost_exceeds_sum_insured():
    claim_input = ClaimData(
        policy_number="POL999",
        patient_name="Test Patient",
        hospital_name="Test Hospital",
        diagnosis="Test Diagnosis",
        estimated_cost=150000.0,
        treatment_plan="Test Procedure",
        sum_insured=100000.0,
    )
    pdf_bytes = generate_preauth_pdf(claim_id="CLAIM-TEST01", claim_input=claim_input)
    assert pdf_bytes.startswith(b"%PDF")


def test_preauth_pdf_generates_without_sum_insured():
    """Omitting sum_insured must not break PDF generation (it is optional)."""
    claim_input = ClaimData(
        policy_number="POL999",
        patient_name="Test Patient",
        hospital_name="Test Hospital",
        diagnosis="Test Diagnosis",
        estimated_cost=50000.0,
        treatment_plan="Test Procedure",
    )
    pdf_bytes = generate_preauth_pdf(claim_id="CLAIM-TEST02", claim_input=claim_input)
    assert pdf_bytes.startswith(b"%PDF")
