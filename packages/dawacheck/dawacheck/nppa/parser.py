"""
NPPA Schedule-I PDF parser.

Parses NPPA Schedule-I ceiling-price PDFs into structured medicine records.
"""

import csv
import re
from pathlib import Path
from typing import Dict, List

import pdfplumber


NPPA_COLUMNS = [
    "sl_no",
    "medicine",
    "dosage_form_strength",
    "unit",
    "ceiling_price",
    "existing_so_no",
    "existing_so_date",
]

EXPECTED_NPPA_ENTRIES = 748


def parse_nppa_pdf(pdf_path: str | Path) -> List[Dict[str, str]]:
    """Parse an NPPA Schedule-I PDF into structured records."""

    all_rows: List[List[str]] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()

            for table in tables:
                if not table:
                    continue

                for row in table:
                    if not row:
                        continue

                    cells = [
                        re.sub(r"\s+", " ", (cell or "")).strip()
                        for cell in row
                    ]

                    # Skip empty rows.
                    if not any(cells):
                        continue

                    # Find rows beginning with a serial number 1–748.
                    if re.fullmatch(r"\d{1,3}", cells[0] or ""):
                        sl_no = int(cells[0])

                        if 1 <= sl_no <= EXPECTED_NPPA_ENTRIES:
                            all_rows.append(cells)

    # Remove duplicate rows while preserving order.
    unique_rows: List[List[str]] = []
    seen = set()

    for row in all_rows:
        key = tuple(row)

        if key not in seen:
            seen.add(key)
            unique_rows.append(row)

    # Keep only actual NPPA entries.
    rows: List[List[str]] = []

    for row in unique_rows:
        if not row:
            continue

        try:
            sl_no = int(row[0])
        except (TypeError, ValueError):
            continue

        if 1 <= sl_no <= EXPECTED_NPPA_ENTRIES:
            rows.append(row)

    # Sort by serial number.
    rows.sort(key=lambda row: int(row[0]))

    output: List[Dict[str, str]] = []

    for row in rows:
        # Expected columns:
        # SL NO | MEDICINE | DOSAGE FORM & STRENGTH | UNIT |
        # CEILING PRICE | EXISTING S.O. NO. & DATE
        if len(row) < 6:
            continue

        sl_no = row[0]
        medicine = row[1]
        dosage_form_strength = row[2]
        unit = row[3]
        ceiling_price = row[4]

        # Last PDF column contains S.O. number + date.
        so_text = " ".join(row[5:]).strip()

        match = re.search(
            r"(\d+\(E\))\s+(\d{2}-\d{2}-\d{4})",
            so_text,
        )

        if not match:
            continue

        existing_so_no = match.group(1)
        existing_so_date = match.group(2)

        output.append(
            {
                "sl_no": sl_no,
                "medicine": medicine,
                "dosage_form_strength": dosage_form_strength,
                "unit": unit,
                "ceiling_price": ceiling_price,
                "existing_so_no": existing_so_no,
                "existing_so_date": existing_so_date,
            }
        )

    # Validate the complete NPPA Schedule-I table.
    if len(output) != EXPECTED_NPPA_ENTRIES:
        raise ValueError(
            f"Expected {EXPECTED_NPPA_ENTRIES} entries, "
            f"but extracted {len(output)}"
        )

    serials = [int(record["sl_no"]) for record in output]

    if serials != list(range(1, EXPECTED_NPPA_ENTRIES + 1)):
        raise ValueError(
            "Serial numbers are not continuous from 1 to 748"
        )

    return output


def write_nppa_csv(
    records: List[Dict[str, str]],
    output_path: str | Path,
) -> None:
    """Write parsed NPPA records to a CSV file."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=NPPA_COLUMNS,
        )

        writer.writeheader()
        writer.writerows(records)