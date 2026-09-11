"""Regression tests for shared billing line-item parsing.

Every case here corresponds to a defect found by live end-to-end probes during the
2026-09-11 repository audit.
"""

from kadi.line_items import (
    extract_total_amount,
    is_noise_name,
    is_summary_line,
    looks_like_medicine,
    normalise_amount,
    parse_line_item,
    parse_line_items,
)

AUDIT_PROBE_BILL = """Lifeline Multispeciality Hospital
Patient Name: Ramesh Kulkarni
Diagnosis: Acute Appendicitis
Consultation: 900
ICU: 18500
Blood Test: 750
Dolo 650: 33
Total Amount: 20183
"""


def test_icu_line_is_not_dropped():
    """`ICU` is 3 chars; the old `len(name) > 3` filter deleted it silently."""
    item = parse_line_item("ICU: 18500")
    assert item is not None, "ICU line must not be filtered out as noise"
    assert item["item"] == "ICU"
    assert item["charged"] == 18500.0


def test_dosage_is_not_parsed_as_price():
    """`Dolo 650: 33` previously yielded (name='Dolo', charged=650.0)."""
    item = parse_line_item("Dolo 650: 33")
    assert item is not None
    assert item["item"] == "Dolo 650"
    assert item["charged"] == 33.0


def test_audit_probe_bill_totals_correctly():
    """The probe bill reported 1650.0 of a 20183 bill. Every charge must now be captured."""
    items = parse_line_items(AUDIT_PROBE_BILL)
    by_name = {i["item"]: i["charged"] for i in items}

    assert by_name == {
        "Consultation": 900.0,
        "ICU": 18500.0,
        "Blood Test": 750.0,
        "Dolo 650": 33.0,
    }
    assert sum(by_name.values()) == 20183.0


def test_summary_and_metadata_lines_excluded():
    assert parse_line_item("Total Amount: 20183") is None
    assert parse_line_item("Grand Total: 5000") is None
    assert parse_line_item("Subtotal: 1200") is None
    assert parse_line_item("Net Payable: 900") is None
    assert parse_line_item("Tax: 250") is None
    assert parse_line_item("CGST: 90") is None
    assert parse_line_item("Invoice No: 4471") is None


def test_date_lines_are_not_charges():
    """`Date: 2024-01-15` used to parse as an item costing 15.0."""
    assert parse_line_item("Date: 2024-01-15") is None
    assert parse_line_item("Admission Date: 2024-03-02") is None


def test_non_charge_lines_ignored():
    assert parse_line_item("Patient Name: Ramesh Kulkarni") is None
    assert parse_line_item("Diagnosis: Acute Appendicitis") is None
    assert parse_line_item("Denial Code: DEN-4471") is None
    assert parse_line_item("") is None


def test_short_noise_still_filtered():
    """Filtering noise must survive the ICU fix."""
    assert parse_line_item("AB: 100") is None
    assert parse_line_item("Dr: 500") is None
    assert is_noise_name("AB")
    assert is_noise_name("12")
    assert not is_noise_name("ICU")
    assert not is_noise_name("Consultation")


def test_currency_and_thousand_separators():
    assert parse_line_item("Room Rent: ₹2,500.00") == {"item": "Room Rent", "charged": 2500.0}
    assert parse_line_item("Nursing Charges Rs. 1,200") == {
        "item": "Nursing Charges",
        "charged": 1200.0,
    }
    assert parse_line_item("Oxygen INR 750") == {"item": "Oxygen", "charged": 750.0}
    assert normalise_amount("1,23,456.78") == 123456.78


def test_extract_total_amount_prefers_real_total_over_tax():
    text = "Consultation: 900\nTotal Tax: 120\nTotal Amount: 20183\n"
    assert extract_total_amount(text) == 20183.0


def test_extract_total_amount_absent_returns_zero():
    assert extract_total_amount("Consultation: 900\n") == 0.0


def test_summary_helper_is_case_and_colon_insensitive():
    assert is_summary_line("TOTAL AMOUNT")
    assert is_summary_line("  grand total ")
    assert not is_summary_line("Pharmacy Charges")
    assert not is_summary_line("Consultation Fee")


def test_medicine_classification():
    assert looks_like_medicine("Dolo 650")
    assert looks_like_medicine("Paracetamol IV Infusion 100ml")
    assert looks_like_medicine("Inj Meropenem")
    assert looks_like_medicine("Amoxicillin 500mg Capsule")
    assert not looks_like_medicine("ICU")
    assert not looks_like_medicine("Consultation")
    assert not looks_like_medicine("Blood Test")


def test_bare_number_not_treated_as_drug_strength_for_rooms():
    """`Dolo 650` is a medicine; `Room 302` is not."""
    assert not looks_like_medicine("Room 302")
    assert not looks_like_medicine("Ward 12")
    assert not looks_like_medicine("Bed 45")
    assert looks_like_medicine("Pan 40")
