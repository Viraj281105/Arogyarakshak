import pdfplumber
import csv
import re

PDF = "data/raw/NPPA.pdf"
OUT = "data/raw/NPPA_schedule_2025.csv"

all_rows = []

with pdfplumber.open(PDF) as pdf:
    for page_no, page in enumerate(pdf.pages, start=1):

        tables = page.extract_tables()

        for table in tables:
            if not table:
                continue

            for row in table:

                if not row:
                    continue

                cells = [
                    re.sub(r'\s+', ' ', (cell or '')).strip()
                    for cell in row
                ]

                # Skip empty rows
                if not any(cells):
                    continue

                # Find rows beginning with a serial number 1–748
                if re.fullmatch(r'\d{1,3}', cells[0] or ''):
                    sl_no = int(cells[0])

                    if 1 <= sl_no <= 748:
                        all_rows.append(cells)

# Remove duplicate rows while preserving order
unique = []
seen = set()

for row in all_rows:
    key = tuple(row)
    if key not in seen:
        seen.add(key)
        unique.append(row)

# Keep only actual NPPA entries
rows = []

for row in unique:
    if not row:
        continue

    try:
        sl_no = int(row[0])
    except:
        continue

    if 1 <= sl_no <= 748:
        rows.append(row)

# Sort by serial number
rows.sort(key=lambda x: int(x[0]))

# The PDF's table has:
# SL NO | MEDICINE | DOSAGE FORM & STRENGTH | UNIT | CEILING PRICE | EXISTING S.O. NO. & DATE

output = []

for row in rows:

    # We expect at least 6 columns
    if len(row) < 6:
        print("WARNING: fewer than 6 columns:", row)
        continue

    sl_no = row[0]
    medicine = row[1]
    dosage_form_strength = row[2]
    unit = row[3]
    ceiling_price = row[4]

    # Last PDF column contains S.O. number + date
    so_text = " ".join(row[5:]).strip()

    m = re.search(
        r'(\d+\(E\))\s+(\d{2}-\d{2}-\d{4})',
        so_text
    )

    if not m:
        print("WARNING: Could not split S.O. number/date:", row)
        continue

    existing_so_no = m.group(1)
    existing_so_date = m.group(2)

    output.append({
        "sl_no": sl_no,
        "medicine": medicine,
        "dosage_form_strength": dosage_form_strength,
        "unit": unit,
        "ceiling_price": ceiling_price,
        "existing_so_no": existing_so_no,
        "existing_so_date": existing_so_date
    })

# Validate
if len(output) != 748:
    raise ValueError(
        f"Expected 748 entries, but extracted {len(output)}"
    )

serials = [int(r["sl_no"]) for r in output]

if serials != list(range(1, 749)):
    raise ValueError("Serial numbers are not continuous from 1 to 748")

# Write CSV
with open(OUT, "w", newline="", encoding="utf-8-sig") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "sl_no",
            "medicine",
            "dosage_form_strength",
            "unit",
            "ceiling_price",
            "existing_so_no",
            "existing_so_date"
        ]
    )

    writer.writeheader()
    writer.writerows(output)

print()
print("SUCCESS")
print("Created:", OUT)
print("Rows:", len(output))
print()

for n in [1, 354, 355, 356, 357, 358, 359, 360, 361, 748]:

    r = output[n - 1]

    print(f"Row {n}:")
    print(r)
    print()

print("VALIDATION PASSED")
