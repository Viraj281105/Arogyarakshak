"""DawaCheck explanation: built from the benchmark's own fields (ADR-015)."""

from dawacheck.checker import benchmark_medicine
from dawacheck.explain import explain_medicine
from kadi.explanation import ProvenanceClass


def _facts(exp, kind):
    rule = next(r for r in exp.rules if r.kind == kind)
    return {f.label: f.value for f in rule.facts}


def test_compared_overcharge_explains_the_row_and_basis():
    b = benchmark_medicine("Dolo 650", 5.0, price_basis="PER_UNIT")
    exp = explain_medicine(
        brand_name="Dolo 650", benchmark=b, name_provenance=ProvenanceClass.USER_ENTERED,
        trust_code="USER_ENTERED", trust_label="Entered by you", entered_by_user=True,
    )
    assert exp.finding_type == "DAWACHECK_MEDICINE"
    assert "above the reference ceiling" in exp.headline
    row = _facts(exp, "REFERENCE_TABLE_ROW")
    assert row["Ceiling price"].startswith("₹2.30")
    assert row["How the name was matched"].startswith("Direct match")
    # The reference table carries no NPPA serial: reported, not invented.
    assert row["NPPA notification / serial number for this row"] is None
    assert any("NPPA notification / serial number" in n for n in exp.not_recorded)


def test_cannot_compare_reports_the_recorded_reason_and_no_verdict():
    b = benchmark_medicine("Dolo 650", 60.0, price_facts=None, read_name_for_quantity=True, allow_api_default=False)
    assert b is not None and b.comparison_status.value == "CANNOT_COMPARE"
    exp = explain_medicine(
        brand_name="Dolo 650", benchmark=b, name_provenance=ProvenanceClass.OCR_EXTRACTED,
        trust_code="MACHINE_EXTRACTED", trust_label="Machine-extracted", source_file="bill.pdf",
    )
    assert "could not be compared" in exp.headline
    reason = next(u for u in exp.undetermined if u.code == b.comparison_reason_code)
    assert reason.reason == b.comparison_note
    assert exp.evidence[0].document == "bill.pdf"


def test_held_back_medicine_shows_the_gate_reason_and_unrecorded_amount():
    exp = explain_medicine(
        brand_name="Pan 4O", benchmark=None, name_provenance=ProvenanceClass.OCR_EXTRACTED,
        trust_code="OCR_UNCERTAIN", trust_label="Unclear on the document",
        not_compared_note="Part of this entry was read with low confidence.", billed_amount=None,
        ocr_reasons=["AMBIGUOUS"],
    )
    codes = [u.code for u in exp.undetermined]
    assert codes[0] == "HELD_BY_TRUST_GATE" and "OCR_AMBIGUOUS" in codes
    assert "Billed amount" in exp.not_recorded
    assert exp.rules == []


def test_no_note_means_not_recorded_not_a_made_up_reason():
    exp = explain_medicine(
        brand_name="X", benchmark=None, name_provenance=ProvenanceClass.OCR_EXTRACTED,
        trust_code="OCR_UNCERTAIN", trust_label="l",
    )
    assert "did not record why" in exp.undetermined[0].reason
