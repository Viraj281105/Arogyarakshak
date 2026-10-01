from pathlib import Path

import pytest

from dawacheck.nppa.parser import parse_nppa_pdf


PROJECT_ROOT = Path(__file__).resolve().parents[3]
NPPA_PDF = PROJECT_ROOT / "data" / "raw" / "NPPA.pdf"


@pytest.mark.skipif(
    not NPPA_PDF.exists(),
    reason="NPPA reference PDF is not available",
)
def test_parse_nppa_pdf_returns_748_entries() -> None:
    """The official 2025 NPPA PDF must contain 748 formulations."""

    records = parse_nppa_pdf(NPPA_PDF)

    assert len(records) == 748


@pytest.mark.skipif(
    not NPPA_PDF.exists(),
    reason="NPPA reference PDF is not available",
)
def test_parse_nppa_pdf_has_continuous_serial_numbers() -> None:
    """NPPA serial numbers must run continuously from 1 to 748."""

    records = parse_nppa_pdf(NPPA_PDF)

    serial_numbers = [
        int(record["sl_no"])
        for record in records
    ]

    assert serial_numbers == list(range(1, 749))


@pytest.mark.skipif(
    not NPPA_PDF.exists(),
    reason="NPPA reference PDF is not available",
)
def test_parse_nppa_pdf_contains_expected_first_and_last_rows() -> None:
    """Verify representative records from the official NPPA table."""

    records = parse_nppa_pdf(NPPA_PDF)

    assert records[0]["sl_no"] == "1"
    assert records[0]["medicine"] == "5-aminosalicylic Acid"
    assert records[0]["ceiling_price"] == "8.06"

    assert records[-1]["sl_no"] == "748"
    assert records[-1]["medicine"] == "Zolpidem"
    assert records[-1]["ceiling_price"] == "8.66"