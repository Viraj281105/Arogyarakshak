import pytest
from daavisetu.generator import generate_claim_package, ClaimData


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
