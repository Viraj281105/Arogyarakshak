"""BimaNyay clinical-interpretation trigger (ADR-011)."""

from bimanyay import ClaimDenialInput, analyze_insurance_denial, assess_clinical_review_need


def test_investigation_only_requires_clinical_interpretation():
    t = assess_clinical_review_need("INVESTIGATION_ONLY", "Admission for investigation only", "Pneumonia")
    assert t.requires_clinical_interpretation is True
    assert t.suggested_clinical_question and "Pneumonia" in t.suggested_clinical_question


def test_medical_necessity_wording_is_detected_regardless_of_category():
    t = assess_clinical_review_need("EXCLUSION_CLAUSE", "Treatment not medically necessary", "Fracture")
    assert t.requires_clinical_interpretation is True


def test_administrative_denials_do_not_trigger():
    t = assess_clinical_review_need("DELAYED_INTIMATION", "Claim intimated after 30 days", "Fracture")
    assert t.requires_clinical_interpretation is False
    assert t.suggested_clinical_question is None


def test_trigger_never_predicts_outcome():
    t = assess_clinical_review_need("PED_NON_DISCLOSURE", "Pre-existing disease", "Diabetes")
    assert "does not predict" in t.note


def test_analysis_result_carries_the_trigger():
    result = analyze_insurance_denial(
        ClaimDenialInput(
            policy_number="P1", insurer_name="Acme", policy_age_years=2, claimed_amount=10000,
            denied_or_deducted_amount=10000, denial_category="INVESTIGATION_ONLY",
            denial_reason_raw="Hospitalisation for investigation only", diagnosis="Fever",
        )
    )
    assert result.clinical_review is not None
    assert result.clinical_review.requires_clinical_interpretation is True
