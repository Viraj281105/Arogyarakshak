"""DawaCheck price basis: a billed amount is compared with a per-unit NPPA ceiling only
after it has been resolved to a price per unit — otherwise CANNOT_COMPARE, never a guess.

Regression context: a strip price (₹33 for 15 tablets) was compared with the ₹2.30
per-tablet ceiling and reported as "overcharged by 1,335%".
"""

import pytest

from dawacheck.checker import benchmark_medicine
from dawacheck.price_basis import (
    ComparisonStatus,
    PriceBasis,
    annotate_medicine_price_facts,
    compare_with_ceiling,
    document_price_statement,
    parse_quantity_text,
    resolve_billed_price,
)


def _bench(name, amount, **kw):
    result = benchmark_medicine(name, amount, **kw)
    assert result is not None, f"{name} should match a reference entry"
    return result


# --- Comparable bases -------------------------------------------------------------------


def test_unit_price_vs_unit_ceiling_is_compared_directly():
    r = _bench("Dolo 650", 2.10, price_basis="PER_UNIT")
    assert r.comparison_status == ComparisonStatus.COMPARED
    assert r.price_basis == PriceBasis.PER_UNIT
    assert r.basis_source == "DECLARED"
    assert r.billed_unit_price == 2.10
    assert r.nppa_ceiling_price == 2.30
    assert r.unit_label == "tablet"
    assert r.price_basis_label == "per tablet"
    assert r.is_overcharged is False
    assert r.deviation_percentage == 0.0


def test_strip_price_with_stated_size_is_converted_before_comparison():
    r = _bench("Dolo 650", 33.0, price_basis="PER_STRIP", units_per_pack=15)
    assert r.comparison_status == ComparisonStatus.COMPARED
    assert r.mrp == 33.0  # as billed
    assert r.billed_unit_price == 2.2
    assert r.price_basis_label == "per strip of 15"
    assert r.is_overcharged is False


def test_two_strip_prices_of_the_same_size_compare_consistently():
    # Strip vs strip: the same strip price always maps to the same unit verdict, and a
    # dearer strip is above the ceiling by exactly its per-unit excess.
    cheap = _bench("Pan 40", 45.0, price_basis="PER_STRIP", units_per_pack=15)
    dear = _bench("Pan 40", 60.0, price_basis="PER_STRIP", units_per_pack=15)
    assert cheap.billed_unit_price == 3.0 and cheap.is_overcharged is False
    assert dear.billed_unit_price == 4.0 and dear.is_overcharged is True
    assert dear.deviation_percentage == 25.0  # (4.00 - 3.20) / 3.20


def test_pack_price_with_stated_size_is_converted():
    r = _bench("Augmentin 625", 220.0, price_basis="PER_PACK", units_per_pack=10)
    assert r.billed_unit_price == 22.0
    assert r.price_basis_label == "per pack of 10"
    assert r.is_overcharged is True
    assert r.deviation_percentage == pytest.approx(9.45, abs=0.01)


def test_pack_notation_in_the_name_is_read_as_a_pack():
    # "(15s)" is Indian pack notation; ₹33.50 for 15 tablets is ₹2.23 each (within).
    r = _bench("Dolo 650mg Tablet (15s)", 33.5)
    assert r.price_basis == PriceBasis.PER_PACK
    assert r.basis_source == "DOCUMENT_LINE"
    assert r.billed_unit_price == 2.23
    assert r.is_overcharged is False


def test_line_total_for_a_stated_number_of_units_is_divided():
    r = _bench("Dolo 650", 25.0, price_basis="LINE_TOTAL", quantity=10)
    assert r.billed_unit_price == 2.5
    assert r.price_basis_label == "total for 10 tablets"
    assert r.is_overcharged is True


def test_legacy_manual_contract_is_labelled_not_hidden():
    # A caller that sends no basis, with a name stating no pack, gets the documented
    # per-unit contract — and the response says that is where the basis came from.
    r = _bench("Dolo 650", 3.5)
    assert r.basis_source == "API_DEFAULT"
    assert r.is_overcharged is True
    assert r.deviation_percentage == 52.17


# --- Incompatible or missing information -> CANNOT_COMPARE -----------------------------


def _assert_cannot_compare(r, code):
    assert r.comparison_status == ComparisonStatus.CANNOT_COMPARE
    assert r.comparison_reason_code == code
    assert r.is_overcharged is None
    assert r.deviation_percentage is None
    assert r.billed_unit_price is None
    assert r.comparison_note
    # The ceiling itself is still shown, per unit, so the person can check by hand.
    assert r.nppa_ceiling_price > 0


def test_strip_price_without_pack_size_is_not_compared():
    _assert_cannot_compare(_bench("Dolo 650", 33.0, price_basis="PER_STRIP"), "PACK_SIZE_MISSING")


def test_unknown_basis_from_a_document_is_not_compared():
    # What the case route does for a bill line with no basis: no legacy default.
    _assert_cannot_compare(_bench("Dolo 650", 33.0, allow_api_default=False), "BASIS_UNKNOWN")
    _assert_cannot_compare(_bench("Dolo 650", 33.0, price_basis="UNKNOWN", allow_api_default=False), "BASIS_UNKNOWN")


def test_line_total_without_quantity_is_not_compared():
    _assert_cannot_compare(_bench("Dolo 650", 33.0, price_basis="LINE_TOTAL"), "QUANTITY_MISSING")


@pytest.mark.parametrize("bad", [0, -2, 2.5])
def test_zero_negative_or_fractional_quantity_is_refused(bad):
    _assert_cannot_compare(_bench("Dolo 650", 33.0, price_basis="LINE_TOTAL", quantity=bad), "INVALID_QUANTITY")
    _assert_cannot_compare(_bench("Dolo 650", 33.0, price_basis="PER_STRIP", units_per_pack=bad), "INVALID_QUANTITY")


def test_zero_quantity_stated_in_a_bill_line_is_refused():
    _assert_cannot_compare(_bench("Dolo 650 Qty: 0", 33.0, allow_api_default=False), "INVALID_QUANTITY")


@pytest.mark.parametrize("amount", [0, -5])
def test_non_positive_amount_is_refused(amount):
    _assert_cannot_compare(_bench("Dolo 650", amount, price_basis="PER_UNIT"), "INVALID_AMOUNT")


def test_per_unit_declaration_contradicted_by_the_name_is_refused():
    # The person chose "per tablet" but typed a pack name: the old code reported +1,356%.
    _assert_cannot_compare(_bench("Dolo 650mg Tablet (15s)", 33.5, price_basis="PER_UNIT"), "BASIS_CONTRADICTS_NAME")


def test_quantity_and_pack_size_together_are_ambiguous():
    # "Qty 2" beside "strip of 10": bills differ on whether the 2 counts strips or tablets.
    _assert_cannot_compare(_bench("Pan 40 strip of 10 Qty 2", 120.0, allow_api_default=False), "CONFLICTING_QUANTITY")


def test_two_different_pack_sizes_are_a_conflict():
    _assert_cannot_compare(_bench("Pan 40 strip of 10 pack of 15", 120.0, allow_api_default=False), "CONFLICTING_QUANTITY")


def test_dosage_form_mismatch_is_not_compared():
    # A tablet ceiling says nothing about an injection's price.
    _assert_cannot_compare(_bench("Inj Pan 40", 45.0, price_basis="PER_UNIT"), "DOSAGE_FORM_MISMATCH")
    _assert_cannot_compare(_bench("Tab Meropenem 1g", 900.0, price_basis="PER_UNIT"), "DOSAGE_FORM_MISMATCH")


# --- Reading documents ------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Tab Augmntn 625mg 1-0-1 x 5 days",  # a dosing schedule, not a quantity
        "Tab Pan 40 1-0-0",
        "Tab Dolo 650 SOS",
        "Paracetamol 650mg",  # the strength is not a quantity
    ],
)
def test_dosing_schedules_and_strengths_are_not_read_as_quantities(text):
    facts = parse_quantity_text(text)
    assert facts.basis is None and facts.conflict is None and facts.quantity is None


@pytest.mark.parametrize(
    "text, basis, size, qty",
    [
        ("Tab Pan 40 (Strip of 15)", PriceBasis.PER_STRIP, 15, None),
        ("Metformin 500mg 10 tabs/strip", PriceBasis.PER_STRIP, 10, None),
        ("Pan 40 strip of 10 tablets", PriceBasis.PER_STRIP, 10, None),
        ("Dolo 650 Tablet 15's", PriceBasis.PER_PACK, 15, None),
        ("Pan 40 1x15", PriceBasis.PER_PACK, 15, None),
        ("Augmentin 625 box of 10", PriceBasis.PER_PACK, 10, None),
        ("Dolo 650 Qty: 10", PriceBasis.LINE_TOTAL, None, 10),
        ("Dolo 650 x 10 tabs", PriceBasis.LINE_TOTAL, None, 10),
        ("Dolo 650 /tab", PriceBasis.PER_UNIT, None, None),
    ],
)
def test_quantity_statements_are_read(text, basis, size, qty):
    facts = parse_quantity_text(text)
    assert facts.basis == basis
    assert facts.units_per_pack == size
    assert facts.quantity == qty
    assert facts.evidence


def test_document_rate_heading_sets_the_basis_for_lines_that_state_none():
    text = "Rx Rate per tablet/capsule (Rs)\nTab Augmntn 625mg 1-0-1 x 5 days 22.00\nTab Pan 40 (Strip of 15) 45.00"
    statement = document_price_statement(text)
    assert statement is not None and statement.basis == PriceBasis.PER_UNIT
    meds = [
        {"name": "Augmentin 625", "cost": 22.0, "source_line": "Tab Augmntn 625mg 1-0-1 x 5 days"},
        {"name": "Pan 40", "cost": 45.0, "source_line": "Tab Pan 40 (Strip of 15)"},
    ]
    annotate_medicine_price_facts(meds, text)
    assert meds[0]["price_facts"]["basis"] == "PER_UNIT"
    assert meds[0]["price_facts"]["source"] == "document"
    # The line's own statement wins over the heading.
    assert meds[1]["price_facts"]["basis"] == "PER_STRIP"
    assert meds[1]["price_facts"]["units_per_pack"] == 15
    # The raw line is not kept.
    assert all("source_line" not in m for m in meds)


def test_a_document_stating_two_bases_does_not_speak_for_every_line():
    assert document_price_statement("Rate per tablet\nPrice per strip") is None


def test_stored_facts_drive_the_case_comparison():
    facts = parse_quantity_text("Tab Pan 40 (Strip of 15)").model_dump(mode="json")
    r = _bench("Pan 40", 60.0, price_facts=facts, read_name_for_quantity=False, allow_api_default=False)
    assert r.basis_source == "DOCUMENT_LINE"
    assert r.billed_unit_price == 4.0
    assert r.is_overcharged is True


def test_compare_with_ceiling_never_mixes_bases():
    billed = resolve_billed_price(120.0, declared_basis="PER_STRIP")  # size missing
    out = compare_with_ceiling(billed, 3.20, "tablet")
    assert out.status == ComparisonStatus.CANNOT_COMPARE
    assert out.deviation_percentage is None
