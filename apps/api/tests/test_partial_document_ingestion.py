"""Wave 2 (stream A, integrated): a partially read document must never look complete.

The parser reports `partial`, `partial_reason` and `warnings` (counts and fixed wording only).
Ingestion must carry them into the case's extraction warnings and the final status line, so a
bill read from only some of its pages is flagged for review instead of reported as processed."""

import json

from app.services import case_ingestion
from tests.clinical_helpers import K, client

TEXT = "Hospital bill\nConsultation 500\nX-Ray 400\nTotal 900\n"


def _parse(partial, reason=None, warnings=()):
    def fake(file_bytes, filename):
        return {
            "extraction_ok": True,
            "full_text_content": TEXT,
            "line_items": [{"item": "Consultation", "charged": 500.0}, {"item": "X-Ray", "charged": 400.0}],
            "ocr_segments": [],
            "partial": partial,
            "partial_reason": reason,
            "warnings": list(warnings),
        }
    return fake


def _upload_and_read(monkeypatch, parse):
    monkeypatch.setattr(case_ingestion, "parse_document", parse)
    case_id = client.post(f"{K}/cases", json={"consent_opt_in": True}).json()["id"]
    assert client.post(f"{K}/cases/{case_id}/upload", files={"file": ("bill.pdf", b"%PDF-fake")}).status_code == 202
    stream = client.get(f"{K}/cases/{case_id}/stream")
    events = [json.loads(line[6:]) for line in stream.text.splitlines() if line.startswith("data: ")]
    case = client.get(f"{K}/cases/{case_id}").json()
    return events, case


def test_a_partial_document_is_flagged_in_the_final_status_and_the_case(monkeypatch):
    events, case = _upload_and_read(
        monkeypatch,
        _parse(True, "3 of 14 pages were read; 11 were skipped", ["Pages were skipped (limit reached)."]),
    )
    final = events[-1]
    assert final["status"] == "completed"
    assert "only part of this document could be read" in final["log"]
    assert "3 of 14 pages" in final["log"]
    assert "flagged for review" in final["log"]
    warnings = " | ".join(str(w) for w in case["case"].get("extraction_warnings", []) or _warnings(case))
    assert "Partial document" in warnings and "Pages were skipped" in warnings


def test_a_complete_document_has_no_partial_warning(monkeypatch):
    events, _case = _upload_and_read(monkeypatch, _parse(False))
    final = events[-1]
    assert final["status"] == "completed"
    assert "only part of this document" not in final["log"]


def test_parser_warnings_reach_the_case_even_when_not_partial(monkeypatch):
    _events, case = _upload_and_read(monkeypatch, _parse(False, None, ["Set OCR_LANGUAGES to read Devanagari pages."]))
    assert "OCR_LANGUAGES" in " | ".join(str(w) for w in _warnings(case))


def _warnings(case):
    """Extraction warnings wherever the case payload carries them."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "extraction_warnings" and isinstance(value, list):
                    found.extend(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(case)
    return found
