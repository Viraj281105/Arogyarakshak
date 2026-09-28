"""Renders demo/documents/C_prescription_uncertain.png — a SYNTHETIC prescription + pharmacy
slip for Scenario C. No real patient, prescriber or clinic.

The committed PNG is the demo artefact: in CLINICAL_DEMO_MODE the API recognises it by its
SHA-256 (apps/api/app/clinical/demo_ocr.py) and replays a recorded OCR/extraction fixture,
so the judge demo never depends on EasyOCR's run-to-run confidence. Re-running this script
with a different Pillow version can change the bytes; if it does, update
DEMO_PRESCRIPTION_SHA256 in demo_ocr.py (a test checks they match).

    python demo/documents/generate_prescription_image.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).with_name("C_prescription_uncertain.png")

LINES = [
    ("Sunrise Family Clinic  (SYNTHETIC DEMO)", 30),
    ("Dr. A. Demo  MBBS  Reg. No. DEMO-000", 22),
    ("Patient: Demo Patient C    Age: 42", 22),
    ("Rx                                    Rate per tablet/capsule (Rs)", 34),
    ("Tab Augmntn 625mg  1-0-1 x 5 days          22.00", 26),
    ("Tab Pan 40  1-0-0                          12.00", 26),
    ("Tab Pan-D  1-0-0                           15.00", 26),
    ("Tab Pan  1-0-0   (faded)", 26),
    ("Cap Amoxycilin 500  1-1-1                   9.00", 26),
    ("Tab Dolo 650  SOS                           2.10", 26),
]


def main() -> None:
    img = Image.new("RGB", (1100, 760), "white")
    draw = ImageDraw.Draw(img)
    y = 40
    for text, size in LINES:
        font = ImageFont.load_default(size=size)
        # Simulate faded handwriting on the uncertain lines.
        faded = any(k in text for k in ("Augmntn", "Amoxycilin", "(faded)"))
        draw.text((60, y), text, fill=(150, 150, 150) if faded else (20, 20, 20), font=font)
        y += size + 30
    mark = ImageFont.load_default(size=20)
    draw.text((60, 715), "SYNTHETIC DOCUMENT FOR DEMONSTRATION ONLY - NOT A REAL PRESCRIPTION", fill=(200, 0, 0), font=mark)
    img.save(OUT, format="PNG", optimize=False)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
