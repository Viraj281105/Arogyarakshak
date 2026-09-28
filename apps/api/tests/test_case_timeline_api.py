"""GET /kadi/cases/{id}/timeline — built from persisted records, access-controlled."""

from pathlib import Path

import pytest

from app.api.v1.endpoints import kadi as kadi_endpoint
from app.config import settings
from tests.clinical_helpers import K, client, register, rh

DOC = Path(__file__).resolve().parents[3] / "demo" / "documents" / "C_prescription_uncertain.png"


@pytest.fixture
def demo_mode(monkeypatch):
    monkeypatch.setattr(settings, "clinical_demo_mode", True)


def _timeline(case_id):
    res = client.get(f"{K}/cases/{case_id}/timeline")
    assert res.status_code == 200, res.text
    return res.json()


def test_timeline_follows_scenario_c_from_upload_to_human_agreement(demo_mode):
    case_id = client.post(f"{K}/cases", json={"consent_opt_in": True}).json()["id"]
    client.post(f"{K}/cases/{case_id}/upload", files={"file": ("C.png", DOC.read_bytes())})

    before = _timeline(case_id)
    labels = [e["label"] for e in before["events"]]
    assert labels[:2] == ["Document received and read", "Information extracted"]
    assert "Unclear reading sent for independent human reading" in labels
    assert "Two independent readers agreed" not in labels, "never claimed before it happens"
    assert before["now"]["medicines"] == 5 and before["now"]["medicines_held_back"] == 4

    task = client.get(f"{K}/cases/{case_id}/transcriptions").json()[0]
    a_id, a = register(category="PHARMACIST", name="Timeline Pharmacist")
    b_id, b = register(category="MEDICAL_TRANSCRIPTIONIST", name="Timeline Scribe", reg=None)
    for rid in (a_id, b_id):
        client.post(f"{K}/cases/{case_id}/transcriptions/{task['task_id']}/assign",
                    json={"reviewer_id": rid, "share_with_reviewer_consent": True})
    for tok in (a, b):
        client.post(f"{K}/transcriptions/{task['task_id']}/readings", json={"value": "Tab Augmentin 625mg 1-0-1 x 5 days"}, headers=rh(tok))

    after = _timeline(case_id)
    labels = [e["label"] for e in after["events"]]
    assert labels.index("Two independent readers agreed") > labels.index("A reader submitted a blind reading")
    times = [e["at"] for e in after["events"]]
    assert times == sorted(times)
    assert after["now"]["medicines_human_reviewed"] == 1
    assert after["now"]["medicines_checkable"] == 2
    # Plain language only: no internal ids or enum names leak into labels.
    for e in after["events"]:
        assert "CASE-" not in e["label"] and "_" not in e["label"]


def test_timeline_reports_a_processing_failure_with_recovery(monkeypatch):
    def broken_parse(file_bytes, filename):
        return {"extraction_ok": False, "extraction_error": "The document could not be read."}

    monkeypatch.setattr(kadi_endpoint, "parse_document", broken_parse)
    case_id = client.post(f"{K}/cases", json={"consent_opt_in": True}).json()["id"]
    client.post(f"{K}/cases/{case_id}/upload", files={"file": ("x.png", b"\x89PNG-not-really")})
    body = _timeline(case_id)
    assert body["failure"]["message"] == "The document could not be read."
    assert body["events"] == [], "a failed document is not shown as received and read"


def test_timeline_requires_the_case_token():
    case_id = client.post(f"{K}/cases", json={"consent_opt_in": True}).json()["id"]
    from fastapi.testclient import TestClient
    from app.main import app

    anonymous = TestClient(app)
    assert anonymous.get(f"{K}/cases/{case_id}/timeline").status_code in (401, 403)
