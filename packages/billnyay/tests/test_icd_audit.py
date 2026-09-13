from billnyay.agents.icd_audit import audit_icd_procedure_consistency


def test_consistent_procedure_for_appendicitis():
    result = audit_icd_procedure_consistency(
        "Acute Appendicitis (K35.8)", ["Laparoscopic Appendectomy"]
    )
    assert result.icd10_code == "K35"
    assert result.status == "consistent"


def test_mismatched_procedure_flagged():
    """A knee-replacement bill against an appendicitis diagnosis is exactly the kind
    of miscoding/upcoding signal this tool exists to surface."""
    result = audit_icd_procedure_consistency(
        "Acute Appendicitis (K35.8)", ["Total Knee Replacement"]
    )
    assert result.icd10_code == "K35"
    assert result.status == "mismatched"


def test_no_procedure_billed_is_distinct_from_mismatched():
    result = audit_icd_procedure_consistency("Acute Appendicitis (K35.8)", [])
    assert result.status == "no_procedure_billed"


def test_code_not_found_when_diagnosis_has_no_icd10_code():
    result = audit_icd_procedure_consistency("Stomach pain", ["Consultation"])
    assert result.icd10_code is None
    assert result.status == "code_not_found"


def test_code_not_in_reference_is_not_treated_as_mismatch():
    """A code this curated table doesn't cover must never be reported as 'mismatched' —
    that would falsely imply a fraud signal where there is simply no reference data."""
    result = audit_icd_procedure_consistency("Diabetes Mellitus (E11.9)", ["Insulin therapy"])
    assert result.icd10_code == "E11"
    assert result.status == "code_not_in_reference"


def test_reference_entry_count_is_disclosed_and_honest():
    result = audit_icd_procedure_consistency("Acute Appendicitis (K35.8)", ["Appendectomy"])
    assert result.reference_entry_count > 0
    assert result.reference_entry_count < 100, "must stay a disclosed curated subset, not claim full ICD-10 coverage"


def test_case_insensitive_procedure_matching():
    result = audit_icd_procedure_consistency("Acute Appendicitis (K35.8)", ["LAPAROSCOPIC APPENDECTOMY"])
    assert result.status == "consistent"
