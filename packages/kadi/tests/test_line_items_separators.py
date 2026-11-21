"""Hyphen separator, trailing text after the amount, and 'Total - N' (Wave 2 / F)."""

import pytest

from kadi.line_items import parse_line_item, parse_line_items


def test_hyphen_separator_drops_the_hyphen_from_the_name():
    assert parse_line_item("Consultation - 400") == {"item": "Consultation", "charged": 400.0}
    assert parse_line_item("Room Rent \u2013 4,500") == {"item": "Room Rent", "charged": 4500.0}
    assert parse_line_item("MRI Brain - Rs. 3500") == {"item": "MRI Brain", "charged": 3500.0}


@pytest.mark.parametrize("line,expected", [
    ("Consultation: 500 (paid)", {"item": "Consultation", "charged": 500.0}),
    ("Consultation: 500 paid", {"item": "Consultation", "charged": 500.0}),
    ("Consultation - 500 (cash)", {"item": "Consultation", "charged": 500.0}),
    ("Blood Test: Rs 250/-", {"item": "Blood Test", "charged": 250.0}),
    ("X-Ray Chest: 350 only", {"item": "X-Ray Chest", "charged": 350.0}),
])
def test_trailing_payment_text_after_the_amount_is_tolerated(line, expected):
    assert parse_line_item(line) == expected


@pytest.mark.parametrize("line", ["Total - 1900", "Total \u2013 1,900", "Grand Total - 1900", "Sub Total - 1000"])
def test_total_with_hyphen_is_a_summary_line_not_a_charge(line):
    assert parse_line_item(line) is None


def test_total_is_not_double_counted_in_a_bill():
    items = parse_line_items("Consultation - 400\nBlood Test - 250\nTotal - 650\n")
    assert [i["item"] for i in items] == ["Consultation", "Blood Test"]
    assert sum(i["charged"] for i in items) == 650.0


def test_trailing_text_never_turns_a_drug_strength_into_a_price():
    # "Pan 40 (Strip of 15)" is a strength and pack size, not a charge of 40.
    assert parse_line_item("Pan 40 (Strip of 15)") is None
    assert parse_line_item("Dolo 650 paid") is None


def test_dates_and_identity_lines_still_rejected():
    assert parse_line_item("Date: 2024-01-15") is None
    assert parse_line_item("Date - 2024-01-15") is None
    assert parse_line_item("Contact: 9876543210") is None


def test_existing_forms_unchanged():
    assert parse_line_item("Dolo 650: 33") == {"item": "Dolo 650", "charged": 33.0}
    assert parse_line_item("Consultation 500") == {"item": "Consultation", "charged": 500.0}
    assert parse_line_item("Dialysis - Session 4") == {"item": "Dialysis - Session", "charged": 4.0}
