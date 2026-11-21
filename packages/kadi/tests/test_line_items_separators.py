"""Hyphen separator, trailing text after the amount, and 'Total - N' (Wave 2 / F)."""

import pytest

from kadi.line_items import is_summary_line, parse_line_item, parse_line_items


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


@pytest.mark.parametrize("line", [
    "Pan 40 (Strip of 15)",     # not a payment word: rejected by the trailer whitelist
    "Dolo 650 paid",            # payment word, space separator, no price marker: PRICE-MARKER GUARD
    "Consultation 500 paid",    # PRICE-MARKER GUARD (a real charge, but without a marker we refuse)
    "Consultation 500 (paid)",  # PRICE-MARKER GUARD
    "Room 4 only",              # PRICE-MARKER GUARD
    "Pan 40 only",              # PRICE-MARKER GUARD
    "Pan 40 (cash)",            # PRICE-MARKER GUARD
])
def test_trailing_text_without_a_price_marker_is_not_read_as_a_charge(line):
    """Only the lines marked PRICE-MARKER GUARD exercise the guard in parse_line_item (they match the
    trailing regex and are rejected there); 'Pan 40 (Strip of 15)' is rejected earlier, by the
    payment-word whitelist."""
    assert parse_line_item(line) is None


def test_price_marker_guard_is_what_rejects_them():
    from kadi.line_items import _LINE_ITEM_RE, _LINE_ITEM_TRAILING_RE
    for line in ("Dolo 650 paid", "Room 4 only", "Pan 40 (cash)"):
        assert not _LINE_ITEM_RE.match(line)
        assert _LINE_ITEM_TRAILING_RE.match(line)  # the regex alone WOULD accept it


def test_trailing_text_with_a_marker_and_stacked_remarks():
    assert parse_line_item("Consult Fee: 500/- (paid)") == {"item": "Consult Fee", "charged": 500.0}
    assert parse_line_item("Consultation Rs 500 paid") == {"item": "Consultation", "charged": 500.0}


def test_em_dash_separator_and_hyphen_edge_cases():
    assert parse_line_item("Consultation — 500") == {"item": "Consultation", "charged": 500.0}
    assert parse_line_item("Consultation -400") is None          # hyphen glued to the amount
    assert parse_line_item("Dolo - 650") == {"item": "Dolo", "charged": 650.0}  # hyphen+spaces IS a price marker
    assert parse_line_item("Dialysis - Session 4") == {"item": "Dialysis - Session", "charged": 4.0}


@pytest.mark.parametrize("line,name", [
    ("Total Knee Replacement - 150000", "Total Knee Replacement"),
    ("Total Hip Replacement 200000", "Total Hip Replacement"),
    ("Discount Coupon Consult - 500", "Discount Coupon Consult"),
])
def test_lines_that_merely_start_with_a_summary_word_are_still_charges(line, name):
    assert parse_line_item(line)["item"] == name


def test_summary_detection_strips_trailing_dashes():
    assert is_summary_line("Total -")
    assert is_summary_line("Sub Total –")
    assert parse_line_item("Sub-total - 1000") is None


def test_name_never_keeps_a_trailing_dash():
    for line in ("Consultation - 400", "Blood Test – 250", "Ward Stay — 1500"):
        assert not parse_line_item(line)["item"].endswith(("-", "–", "—"))


def test_the_two_awkward_pea_bills_extract_exactly():
    from kadi.extraction import run_heuristic_extraction_fallback

    hyphen = run_heuristic_extraction_fallback(
        "Prime Hospital\nPatient Name: Leena Mane\nConsultation - 400\nWard Stay - 1500\nTotal - 1900")
    assert [(p["name"], p["amount"]) for p in hyphen.procedures] == [("Consultation", 400.0), ("Ward Stay", 1500.0)]
    assert hyphen.total_amount == 1900.0

    trailing = run_heuristic_extraction_fallback(
        "Zenith Hospital\nPatient Name: Arjun Nair\nConsultation: 500 (paid)\nMRI Brain: 3500 only\nTotal: 4000")
    assert [(p["name"], p["amount"]) for p in trailing.procedures] == [("Consultation", 500.0), ("MRI Brain", 3500.0)]
    assert trailing.total_amount == 4000.0


def test_dates_and_identity_lines_still_rejected():
    assert parse_line_item("Date: 2024-01-15") is None
    assert parse_line_item("Date - 2024-01-15") is None
    assert parse_line_item("Contact: 9876543210") is None


def test_existing_forms_unchanged():
    assert parse_line_item("Dolo 650: 33") == {"item": "Dolo 650", "charged": 33.0}
    assert parse_line_item("Consultation 500") == {"item": "Consultation", "charged": 500.0}
    assert parse_line_item("Dialysis - Session 4") == {"item": "Dialysis - Session", "charged": 4.0}


def test_a_dash_left_on_the_name_by_a_colon_separator_is_stripped():
    # "Name -: 250": the separator is the colon, so the dash would stay in the name without
    # the explicit trailing-dash strip.
    assert parse_line_item("Blood Test -: 250") == {"item": "Blood Test", "charged": 250.0}
