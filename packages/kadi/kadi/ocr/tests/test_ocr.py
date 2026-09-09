import pytest
from kadi.ocr.ocr_parser import parse_document


def test_parse_document_pdf_fallback():
    mock_pdf_bytes = b"%PDF-1.4 ... mock pdf content ..."
    result = parse_document(file_bytes=mock_pdf_bytes, filename="test_bill.pdf")

    assert "full_text_content" in result
    assert "line_items" in result
    assert result["filename"] == "test_bill.pdf"
    assert "Hospital Bill / Clinical Document text extraction" in result["full_text_content"]


def test_parse_document_line_items_regex(monkeypatch):
    mock_text = (
        "Consultation Fee : 1500.00\n"
        "Pharmacy Charges 2450\n"
        "Total Bill: 3950.00\n"
    )

    class MockPage:
        def get_text(self):
            return mock_text

    class MockDoc:
        def __iter__(self):
            return iter([MockPage()])

    import fitz
    monkeypatch.setattr(fitz, "open", lambda *args, **kwargs: MockDoc())

    result = parse_document(file_bytes=b"dummy", filename="test.pdf")
    assert result["filename"] == "test.pdf"
    assert len(result["line_items"]) == 2

    # Exact item names and parsed float amounts
    items_by_name = {item["item"]: item["charged"] for item in result["line_items"]}
    assert "Consultation Fee" in items_by_name
    assert items_by_name["Consultation Fee"] == 1500.0
    assert "Pharmacy Charges" in items_by_name
    assert items_by_name["Pharmacy Charges"] == 2450.0

    # Stopwords like 'total' should be excluded from line items
    assert not any("Total" in item["item"] for item in result["line_items"])


def test_parse_document_rupee_formatting_and_exclusions(monkeypatch):
    mock_text = (
        "Surgeon Fees: ₹12500.50\n"
        "Oxygen Cylinder ₹750\n"
        "Subtotal: ₹13250.50\n"
        "Tax: ₹250\n"
    )

    class MockPage:
        def get_text(self):
            return mock_text

    class MockDoc:
        def __iter__(self):
            return iter([MockPage()])

    import fitz
    monkeypatch.setattr(fitz, "open", lambda *args, **kwargs: MockDoc())

    result = parse_document(file_bytes=b"dummy", filename="hospital_invoice.pdf")
    items_by_name = {item["item"]: item["charged"] for item in result["line_items"]}

    assert "Surgeon Fees" in items_by_name
    assert items_by_name["Surgeon Fees"] == 12500.50
    assert "Oxygen Cylinder" in items_by_name
    assert items_by_name["Oxygen Cylinder"] == 750.0

    # Exclusions for Subtotal and Tax
    assert "Subtotal" not in items_by_name
    assert "Tax" not in items_by_name


def test_parse_document_noise_filtering(monkeypatch):
    mock_text = (
        "AB: 100\n"  # Too short (<= 3 chars)
        "Dr: 500\n"  # Too short
        "ICU Day Tariff: 8500\n"  # Valid item
    )

    class MockPage:
        def get_text(self):
            return mock_text

    class MockDoc:
        def __iter__(self):
            return iter([MockPage()])

    import fitz
    monkeypatch.setattr(fitz, "open", lambda *args, **kwargs: MockDoc())

    result = parse_document(file_bytes=b"dummy", filename="test_noise.pdf")
    assert len(result["line_items"]) == 1
    assert result["line_items"][0]["item"] == "ICU Day Tariff"
    assert result["line_items"][0]["charged"] == 8500.0


def test_parse_document_multipage_pdf(monkeypatch):
    class MockPage1:
        def get_text(self):
            return "Room Rent Deluxe: 6500.00\n"

    class MockPage2:
        def get_text(self):
            return "Nursing Charges: 1200.00\n"

    class MockDoc:
        def __iter__(self):
            return iter([MockPage1(), MockPage2()])

    import fitz
    monkeypatch.setattr(fitz, "open", lambda *args, **kwargs: MockDoc())

    result = parse_document(file_bytes=b"dummy", filename="multipage.pdf")
    assert len(result["line_items"]) == 2
    items_by_name = {item["item"]: item["charged"] for item in result["line_items"]}
    assert items_by_name["Room Rent Deluxe"] == 6500.0
    assert items_by_name["Nursing Charges"] == 1200.0
    assert "Room Rent Deluxe" in result["full_text_content"]
    assert "Nursing Charges" in result["full_text_content"]


def test_parse_document_image_fallback():
    mock_img_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF"
    result = parse_document(file_bytes=mock_img_bytes, filename="prescription.jpg")
    assert result["filename"] == "prescription.jpg"
    assert "full_text_content" in result
    assert isinstance(result["line_items"], list)


