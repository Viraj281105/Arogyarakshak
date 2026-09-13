"""Regression tests for the Kadi heuristic extraction fallback.

This path had no test coverage at all, and it is the path that actually executes whenever
GROQ_API_KEY is unset. Cases mirror defects observed in live audit probes.
"""

from kadi.extraction import ExtractedEntities, run_heuristic_extraction_fallback

AUDIT_PROBE_BILL = """Lifeline Multispeciality Hospital
Patient Name: Ramesh Kulkarni
Diagnosis: Acute Appendicitis
Consultation: 900
ICU: 18500
Blood Test: 750
Dolo 650: 33
Total Amount: 20183
"""


def test_hospital_name_does_not_span_newlines():
    """Previously produced 'Hospital\\nPatient Name' because \\s matched the newline."""
    result = run_heuristic_extraction_fallback(AUDIT_PROBE_BILL)
    assert result.hospital_name == "Lifeline Multispeciality Hospital"
    assert "\n" not in result.hospital_name
    assert "Patient Name" not in result.hospital_name


def test_patient_and_diagnosis_are_extracted():
    """Both were silently missed by the old fallback."""
    result = run_heuristic_extraction_fallback(AUDIT_PROBE_BILL)
    assert result.patient_name == "Ramesh Kulkarni"
    assert result.diagnosis == "Acute Appendicitis"


def test_total_amount_is_the_stated_total():
    result = run_heuristic_extraction_fallback(AUDIT_PROBE_BILL)
    assert result.total_amount == 20183.0


def test_summary_line_is_not_a_procedure():
    """'Total Amount' was previously emitted as a procedure worth 20183."""
    result = run_heuristic_extraction_fallback(AUDIT_PROBE_BILL)
    names = [p["name"] for p in result.procedures] + [m["name"] for m in result.medicines]
    assert "Total Amount" not in names
    assert not any("total" in n.lower() for n in names)


def test_medicines_and_procedures_are_separated():
    result = run_heuristic_extraction_fallback(AUDIT_PROBE_BILL)

    medicine_names = {m["name"] for m in result.medicines}
    procedure_names = {p["name"] for p in result.procedures}

    assert "Dolo 650" in medicine_names
    assert {"Consultation", "ICU", "Blood Test"} <= procedure_names
    assert medicine_names.isdisjoint(procedure_names)


def test_medicine_cost_is_price_not_dosage():
    result = run_heuristic_extraction_fallback(AUDIT_PROBE_BILL)
    dolo = next(m for m in result.medicines if m["name"] == "Dolo 650")
    assert dolo["cost"] == 33.0


def test_labelled_hospital_field_is_preferred():
    text = "Some Letterhead\nHospital Name: Apollo Speciality Hospital\nConsultation: 500\n"
    result = run_heuristic_extraction_fallback(text)
    assert result.hospital_name == "Apollo Speciality Hospital"


def test_empty_document_returns_empty_entities():
    result = run_heuristic_extraction_fallback("")
    assert isinstance(result, ExtractedEntities)
    assert result.hospital_name is None
    assert result.patient_name is None
    assert result.diagnosis is None
    assert result.procedures == []
    assert result.medicines == []
    assert result.total_amount == 0.0


def test_extraction_matches_ocr_parser_for_same_document():
    """The two stages must not disagree about the same source line."""
    from kadi.ocr.ocr_parser import parse_document

    parsed = parse_document(AUDIT_PROBE_BILL.encode("utf-8"), filename="bill.txt")
    ocr_items = {i["item"]: i["charged"] for i in parsed["line_items"]}

    result = run_heuristic_extraction_fallback(AUDIT_PROBE_BILL)
    extracted = {p["name"]: p["amount"] for p in result.procedures}
    extracted.update({m["name"]: m["cost"] for m in result.medicines})

    assert ocr_items == extracted


# --- Direct-identifier handling in the extraction fallback --------------------

PII_TEXT = (
    "Lifeline Multispeciality Hospital\n"
    "Patient Name: Ramesh Kulkarni\n"
    "Contact: 9876543210\n"
    "Email: ramesh.kulkarni@example.com\n"
    "Aadhaar: 1234 5678 9012\n"
    "Diagnosis: Acute Appendicitis\n"
    "Consultation: 900\n"
)


def test_identity_lines_do_not_become_procedures():
    result = run_heuristic_extraction_fallback(PII_TEXT)
    names = [p["name"] for p in result.procedures] + [m["name"] for m in result.medicines]
    assert names == ["Consultation"]
    for leaked in ("Contact", "Aadhaar", "Email", "Patient Name"):
        assert not any(leaked.lower() in n.lower() for n in names)


# --- Facility-name matching must respect word boundaries ----------------------

def test_clinical_prose_is_not_mistaken_for_a_hospital_name():
    """Substring matching made any line containing "clinical" match the keyword "clinic".

    The bogus name then reached DaaviSetu and was printed on a pre-authorization form.
    """
    assert run_heuristic_extraction_fallback(
        "Some unstructured clinical note with no fields.\n"
    ).hospital_name is None
    assert run_heuristic_extraction_fallback(
        "Clinical Diagnosis: Sepsis\n"
    ).hospital_name is None


def test_real_facility_names_still_resolve():
    cases = {
        "Lifeline Multispeciality Hospital\n": "Lifeline Multispeciality Hospital",
        "Sunrise Clinic, Pune\n": "Sunrise Clinic, Pune",
        "Apollo Medical Centre\n": "Apollo Medical Centre",
        "Ruby Hall Clinic\n": "Ruby Hall Clinic",
    }
    for text, expected in cases.items():
        assert run_heuristic_extraction_fallback(text).hospital_name == expected
