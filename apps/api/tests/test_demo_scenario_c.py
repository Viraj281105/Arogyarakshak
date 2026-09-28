"""Scenario C (demo/scenarios/C_uncertain_ocr_prescription.md), executable.

Uploads the committed synthetic prescription image in CLINICAL_DEMO_MODE. OCR confidences
and extraction are replayed from a recorded fixture (app.clinical.demo_ocr); everything
after that is the real pipeline.
"""

import hashlib
from pathlib import Path

import pytest

from app.clinical.demo_ocr import DEMO_PRESCRIPTION_SHA256, demo_ocr_replay
from app.config import settings
from tests.clinical_helpers import K, client, register, rh

DOC = Path(__file__).resolve().parents[3] / "demo" / "documents" / "C_prescription_uncertain.png"


@pytest.fixture
def demo_mode(monkeypatch):
    monkeypatch.setattr(settings, "clinical_demo_mode", True)


def test_committed_demo_document_matches_the_replay_fixture():
    assert DOC.exists(), "demo/documents/C_prescription_uncertain.png must be committed"
    assert hashlib.sha256(DOC.read_bytes()).hexdigest() == DEMO_PRESCRIPTION_SHA256


def test_replay_is_demo_mode_only():
    assert demo_ocr_replay(DEMO_PRESCRIPTION_SHA256, demo_mode=False) is None
    assert demo_ocr_replay("0" * 64, demo_mode=True) is None
    assert demo_ocr_replay(DEMO_PRESCRIPTION_SHA256, demo_mode=True) is not None


def _upload():
    case_id = client.post(f"{K}/cases", json={"consent_opt_in": True}).json()["id"]
    res = client.post(f"{K}/cases/{case_id}/upload", files={"file": ("C_prescription_uncertain.png", DOC.read_bytes())})
    assert res.status_code == 202, res.text
    return case_id


def _bench(case_id):
    return {r["brand_name"]: r for r in client.get(f"/api/v1/dawacheck/cases/{case_id}/benchmark").json()}


def _read(case_id, task_id, a_value, b_value):
    a_id, a = register(category="PHARMACIST", name="Demo-test Pharmacist")
    b_id, b = register(category="MEDICAL_TRANSCRIPTIONIST", name="Demo-test Scribe", reg=None)
    for rid in (a_id, b_id):
        assert client.post(f"{K}/cases/{case_id}/transcriptions/{task_id}/assign",
                           json={"reviewer_id": rid, "share_with_reviewer_consent": True}).status_code == 200
    # Blind: a HIGH-risk reader never sees the OCR guess.
    view = client.get(f"{K}/transcriptions/assigned", headers=rh(a)).json()
    assert all(v["ocr_candidate"] is None for v in view if v["task_id"] == task_id)
    client.post(f"{K}/transcriptions/{task_id}/readings", json={"value": a_value}, headers=rh(a))
    client.post(f"{K}/transcriptions/{task_id}/readings", json={"value": b_value}, headers=rh(b))


def test_scenario_c_end_to_end(demo_mode):
    case_id = _upload()
    stream = client.get(f"{K}/cases/{case_id}/stream").text
    assert "Demo fixture" in stream, "the replay is disclosed in the processing log"

    tasks = client.get(f"{K}/cases/{case_id}/transcriptions").json()
    assert [t["ocr_candidate"] for t in tasks] == ["Tab Augmntn 625mg 1-0-1 x 5 days"], "one defensible link only"
    assert all("Demo" not in t["masked_context"] for t in tasks), "prescriber/patient lines never reach readers"

    bench = _bench(case_id)
    assert bench["Augmntn 625mg"]["trust"]["state"] == "AWAITING_HUMAN_READING"
    assert bench["Pan 40"]["trust"]["reasons"] == ["AMBIGUOUS"] and bench["Pan-D"]["trust"]["reasons"] == ["AMBIGUOUS"]
    assert bench["Amoxicillin 500"]["trust"]["reasons"] == ["POSSIBLE_MATCH"]
    assert bench["Dolo 650"]["trust"]["state"] == "MACHINE_EXTRACTED" and bench["Dolo 650"]["benchmark"] is not None
    assert all(bench[n]["benchmark"] is None for n in ("Augmntn 625mg", "Pan 40", "Pan-D", "Amoxicillin 500"))

    # Two independent readers agree -> the entry is settled and benchmarked as HUMAN_REVIEWED.
    _read(case_id, tasks[0]["task_id"], "Tab Augmentin 625mg 1-0-1 x 5 days", "tab augmentin 625 mg 1-0-1 x 5 days")
    bench = _bench(case_id)
    resolved = next(r for r in bench.values() if r["entity_id"] == tasks[0]["entity_id"])
    assert resolved["trust"]["state"] == "HUMAN_RESOLVED" and resolved["name_provenance"] == "HUMAN_REVIEWED"
    assert resolved["benchmark"] is not None and resolved["benchmark"]["is_overcharged"] is True, "₹22.00 vs ₹20.10 ceiling"
    # Like with like: the slip's "Rate per tablet/capsule" heading makes ₹22.00 a per-tablet price.
    aug = resolved["benchmark"]
    assert aug["comparison_status"] == "COMPARED" and aug["price_basis"] == "PER_UNIT"
    assert aug["basis_source"] == "DOCUMENT_HEADER" and aug["unit_label"] == "tablet"
    assert aug["billed_unit_price"] == 22.0 and aug["nppa_ceiling_price"] == 20.1
    assert aug["deviation_percentage"] == 9.45

    # Disagreement on a whole-entry reading of the normalised name -> stays blocked.
    amox = bench["Amoxicillin 500"]["entity_id"]
    flag = client.post(f"{K}/cases/{case_id}/transcriptions", json={"entity_id": amox, "field_type": "MEDICINE_NAME"})
    assert flag.status_code in (200, 201), flag.text
    _read(case_id, flag.json()["task_id"], "Amoxycillin 500", "Azithromycin 500")
    row = next(r for r in _bench(case_id).values() if r["entity_id"] == amox)
    assert row["benchmark"] is None and row["trust"]["state"] == "READERS_DISAGREED"


def test_demo_prices_are_per_unit_so_no_false_overcharge(demo_mode):
    """Found during browser verification: pack prices against per-unit NPPA ceilings
    produced a false "+1356% above ceiling" for Dolo 650 in the judge demo."""
    case_id = _upload()
    dolo = _bench(case_id)["Dolo 650"]["benchmark"]
    assert dolo is not None and dolo["is_overcharged"] is False
    assert dolo["comparison_status"] == "COMPARED" and dolo["price_basis_label"] == "per tablet"
    assert dolo["billed_unit_price"] == 2.1 and dolo["nppa_ceiling_price"] == 2.3


def test_held_back_medicines_are_not_price_checked_whatever_their_price_basis(demo_mode):
    """The price basis is only consulted after the trust gate: an unresolved, ambiguous or
    possibly-misread medicine gets no comparison even though its per-tablet basis is known."""
    case_id = _upload()
    bench = _bench(case_id)
    for name in ("Augmntn 625mg", "Pan 40", "Pan-D", "Amoxicillin 500"):
        assert bench[name]["benchmark"] is None, name
        assert bench[name]["trust"]["benchmarkable"] is False, name
