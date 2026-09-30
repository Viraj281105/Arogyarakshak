from kadi.line_items import extract_total_amount, parse_line_item, parse_line_items


def test_page_numbers_are_not_bill_items():
    assert parse_line_item("Page 1") is None
    assert parse_line_item("Page 23") is None


def test_bare_medicine_strength_is_not_charge():
    assert parse_line_item("augmentin 625") is None
    assert parse_line_item("Pan 40") is None
    assert parse_line_item("Dolo 650") is None


def test_real_medicine_charge_with_separator_is_preserved():
    assert parse_line_item("Dolo 650: 33") == {
        "item": "Dolo 650",
        "charged": 33.0,
    }


def test_reference_appendix_numbers_are_not_charges():
    assert parse_line_item("IRDAI (Health Insurance) Regulations, 2016") is None
    assert parse_line_item("- Regulation 27") is None
    assert parse_line_item(
        "Dolo 650, Dolo 650mg, Crocin 650, Crocin 650mg, Calpol 650, Pacimol 650"
    ) is None


def test_vertical_bill_table_is_reconstructed():
    text = """
    SERVICE LINE ITEMS
    #
    Hospital Charge Line
    Qty
    Unit Charged
    Project Benchmark
    Test Status
    01
    OPD Consultation (General / Specialist)
    1
    Rs. 450.00
    Rs. 350.00
    ABOVE BENCHMARK
    02
    ICU Day Charges (NABH)
    2
    Rs. 6200.00
    Rs. 5400.00
    ABOVE BENCHMARK
    03
    Laparoscopic Appendectomy Package
    1
    Rs. 34000.00
    Rs. 28000.00
    ABOVE BENCHMARK
    Page 2
    PHARMACY / MEDICINE STRIP DETAILS
    """
    assert parse_line_items(text) == [
        {"item": "OPD Consultation (General / Specialist)", "charged": 450.0},
        {"item": "ICU Day Charges (NABH)", "charged": 6200.0},
        {"item": "Laparoscopic Appendectomy Package", "charged": 34000.0},
    ]


def test_vertical_total_is_supported():
    text = """
    BILL TOTALS
    NET PAYABLE
    Rs. 483458.80
    """
    assert extract_total_amount(text) == 483458.80
