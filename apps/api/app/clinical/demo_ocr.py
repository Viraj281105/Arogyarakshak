"""
Deterministic OCR replay for the Scenario C demo document (ADR-011 demo infrastructure).

EasyOCR's per-segment confidence varies with the machine, the model download and the
image, so a judge demo that depends on "which words came out uncertain" is not
reproducible. In CLINICAL_DEMO_MODE only, uploading the committed synthetic document
`demo/documents/C_prescription_uncertain.png` (recognised by its exact SHA-256) replays a
recorded OCR result and extraction result instead of running EasyOCR and the LLM.

What is replayed (demo-only): the OCR text, per-segment confidences, and the extraction
output — including one deliberately LLM-style normalisation ("Amoxycilin" -> "Amoxicillin").
What is real: everything after that — entity resolution, the uncertainty plan (linking,
ambiguity, possible matches, cap), human-reading tasks, blind two-reader consensus, the
medicine trust gate and DawaCheck. The SSE log and the audit trail say a fixture was used.

Any other document, and this one outside demo mode, goes through the real OCR path.
"""

from typing import Any, Dict, Optional, Tuple

from kadi.extraction import ExtractedEntities

# SHA-256 of demo/documents/C_prescription_uncertain.png (checked by a test).
DEMO_PRESCRIPTION_SHA256 = "d602bf47f5b382b98bd4534fd58fa2b76551e47fccb0b7f05b34914810983411"

REPLAY_LOG = (
    "Demo fixture: this synthetic document's OCR confidences and extraction were replayed from a "
    "recorded fixture (CLINICAL_DEMO_MODE) so the demonstration is reproducible. Everything after "
    "extraction runs normally."
)

_SEGMENTS = [
    # (text, confidence) — what the OCR engine "read" and how sure it was.
    ("Sunrise Family Clinic (SYNTHETIC DEMO)", 0.93),
    ("Dr. A. Demo MBBS Reg. No. DEMO-000", 0.41),  # low confidence, but prescriber identity: never a task
    ("Patient: Demo Patient C Age: 42", 0.95),
    ("Rx Rate per tablet/capsule (Rs)", 0.97),
    ("Tab Augmntn 625mg 1-0-1 x 5 days", 0.34),  # uncertain; names exactly one medicine -> task
    ("22.00", 0.96),
    ("Tab Pan 40 1-0-0", 0.95),
    ("12.00", 0.97),
    ("Tab Pan-D 1-0-0", 0.94),
    ("15.00", 0.97),
    ("Tab Pan 1-0-0", 0.29),  # uncertain; could be Pan 40 or Pan-D -> both held back
    ("Cap Amoxycilin 500 1-1-1", 0.31),  # uncertain; extraction normalised the name -> held back
    ("9.00", 0.95),
    ("Tab Dolo 650 SOS", 0.96),  # clearly read -> benchmarked as machine-extracted
    ("2.10", 0.98),
]

_TEXT = "\n".join(
    [
        "Sunrise Family Clinic (SYNTHETIC DEMO)",
        "Dr. A. Demo MBBS Reg. No. DEMO-000",
        "Patient: Demo Patient C Age: 42",
        "Rx Rate per tablet/capsule (Rs)",
        "Tab Augmntn 625mg 1-0-1 x 5 days 22.00",
        "Tab Pan 40 1-0-0 12.00",
        "Tab Pan-D 1-0-0 15.00",
        "Tab Pan 1-0-0",
        "Cap Amoxycilin 500 1-1-1 9.00",
        "Tab Dolo 650 SOS 2.10",
        "SYNTHETIC DOCUMENT FOR DEMONSTRATION ONLY - NOT A REAL PRESCRIPTION",
    ]
)


def _parsed() -> Dict[str, Any]:
    return {
        "extraction_ok": True,
        "full_text_content": _TEXT,
        # A prescription is not a hospital bill: no billing line items are replayed.
        # Prices are per tablet/capsule, the unit NPPA ceilings are expressed in.
        "line_items": [],
        "ocr_segments": [{"text": t, "confidence": c, "bbox": None} for t, c in _SEGMENTS],
        "filename": "C_prescription_uncertain.png",
        "demo_fixture": True,
    }


def _extracted() -> ExtractedEntities:
    return ExtractedEntities(
        hospital_name="Sunrise Family Clinic (SYNTHETIC DEMO)",
        diagnosis=None,
        procedures=[],
        medicines=[
            {"name": "Augmntn 625mg", "dosage": "625mg", "cost": 22.0},
            {"name": "Pan 40", "dosage": "40mg", "cost": 12.0},
            {"name": "Pan-D", "dosage": None, "cost": 15.0},
            # What an LLM extractor typically does: silently corrects the spelling.
            {"name": "Amoxicillin 500", "dosage": "500mg", "cost": 9.0},
            {"name": "Dolo 650", "dosage": "650mg", "cost": 2.1},
        ],
        total_amount=60.1,
    )


def demo_ocr_replay(digest: Optional[str], demo_mode: bool) -> Optional[Tuple[Dict[str, Any], ExtractedEntities]]:
    """(parsed document, extraction) for the registered demo document in demo mode, else None."""
    if not demo_mode or digest != DEMO_PRESCRIPTION_SHA256:
        return None
    return _parsed(), _extracted()
