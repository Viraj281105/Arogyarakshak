"""End-to-end OCR trust pipeline (ADR-011 demo-hardening pass).

image -> OCR segments -> uncertain readings -> extraction -> medicine entities ->
tasks / held-back state -> readers -> consensus -> entity -> DawaCheck.

The upload tests stub the two network/CPU-heavy steps (EasyOCR parsing and the LLM
extraction) with deterministic outputs, so the rest of the real pipeline runs unchanged.
Before this pass each "blocked" assertion below failed: readings that matched no
medicine, several medicines, or lay beyond the task cap were dropped and the medicine
was benchmarked as an ordinary AI_DERIVED extraction.
"""

import pytest

from app.api.v1.endpoints import kadi as kadi_endpoint
from kadi.extraction import ExtractedEntities
from tests.clinical_helpers import K, client, register, rh


def _stub_pipeline(monkeypatch, *, segments, medicines, diagnosis=None):
    text = "\n".join(s[0] for s in segments)

    def fake_parse(file_bytes, filename):
        return {
            "extraction_ok": True,
            "full_text_content": text,
            "line_items": [],
            "ocr_segments": [{"text": t, "confidence": c, "bbox": None} for t, c in segments],
        }

    def fake_extract(_text, api_key=None, model=None):
        return ExtractedEntities(
            hospital_name="Synthetic Demo Clinic",
            diagnosis=diagnosis,
            medicines=[dict(m) for m in medicines],
            procedures=[],
        )

    monkeypatch.setattr(kadi_endpoint, "parse_document", fake_parse)
    monkeypatch.setattr(kadi_endpoint, "extract_entities_from_text", fake_extract)


def _upload(monkeypatch, *, segments, medicines):
    _stub_pipeline(monkeypatch, segments=segments, medicines=medicines)
    case_id = client.post(f"{K}/cases", json={"consent_opt_in": True}).json()["id"]
    res = client.post(f"{K}/cases/{case_id}/upload", files={"file": ("rx.png", b"\x89PNG-synthetic-" + repr(segments).encode())})
    assert res.status_code == 202, res.text
    return case_id


def _bench(case_id):
    res = client.get(f"/api/v1/dawacheck/cases/{case_id}/benchmark")
    assert res.status_code == 200, res.text
    return {r["brand_name"]: r for r in res.json()}


def _tasks(case_id):
    return client.get(f"{K}/cases/{case_id}/transcriptions").json()


def _medicine_ids(case_id):
    return {e["name"]: e["id"] for e in client.get(f"{K}/cases/{case_id}").json()["entities"] if e["type"] == "medicine"}


def _two_readers():
    a_id, a = register(category="PHARMACIST", name="Pharm Reader")
    b_id, b = register(category="MEDICAL_TRANSCRIPTIONIST", name="Scribe Reader", reg=None)
    return (a_id, a), (b_id, b)


def _read(case_id, task_id, value_a, value_b):
    (a_id, a), (b_id, b) = _two_readers()
    for rid in (a_id, b_id):
        res = client.post(f"{K}/cases/{case_id}/transcriptions/{task_id}/assign",
                          json={"reviewer_id": rid, "share_with_reviewer_consent": True})
        assert res.status_code == 200, res.text
    client.post(f"{K}/transcriptions/{task_id}/readings", json={"value": value_a}, headers=rh(a))
    client.post(f"{K}/transcriptions/{task_id}/readings", json={"value": value_b}, headers=rh(b))


def _flag_whole_entry(case_id, entity_id):
    res = client.post(f"{K}/cases/{case_id}/transcriptions", json={"entity_id": entity_id, "field_type": "MEDICINE_NAME"})
    assert res.status_code in (200, 201), res.text
    return res.json()["task_id"]


# --- baseline: a clearly read medicine is benchmarked as machine-extracted ----------

def test_clear_prescription_is_benchmarked(monkeypatch):
    case_id = _upload(monkeypatch, segments=[("Tab Dolo 650 1-0-1", 0.95)],
                      medicines=[{"name": "Dolo 650", "cost": 33.5}])
    row = _bench(case_id)["Dolo 650"]
    assert row["benchmark"] is not None
    assert row["trust"]["state"] == "MACHINE_EXTRACTED" and row["name_provenance"] == "AI_DERIVED"


# --- 1. zero-match ------------------------------------------------------------------

def test_zero_match_reading_blocks_an_ungrounded_medicine(monkeypatch):
    case_id = _upload(
        monkeypatch,
        segments=[("Tab Dolo 650 1-0-1", 0.95), ("Tab Zxqvrt 1-0-1", 0.2)],
        medicines=[{"name": "Dolo 650", "cost": 33.5}, {"name": "Augmentin 625", "cost": 220}],
    )
    bench = _bench(case_id)
    assert bench["Dolo 650"]["benchmark"] is not None, "clearly read on the page"
    held = bench["Augmentin 625"]
    assert held["benchmark"] is None and held["trust"]["state"] == "OCR_UNCERTAIN"
    assert held["trust"]["reasons"] == ["UNGROUNDED"]
    assert _tasks(case_id) == [], "no task can be linked, but nothing was silently trusted"


# --- 2. ambiguous -------------------------------------------------------------------

def test_ambiguous_reading_blocks_both_candidates(monkeypatch):
    case_id = _upload(
        monkeypatch,
        segments=[("Pan", 0.3), ("40 mg", 0.95)],
        medicines=[{"name": "Pan 40", "cost": 120}, {"name": "Pan-D", "cost": 150}],
    )
    bench = _bench(case_id)
    for name in ("Pan 40", "Pan-D"):
        assert bench[name]["benchmark"] is None and bench[name]["trust"]["reasons"] == ["AMBIGUOUS"]
    assert _tasks(case_id) == [], "software never picks one candidate"


# --- 3. over-cap --------------------------------------------------------------------

def test_readings_beyond_the_cap_stay_uncertain(monkeypatch):
    names = ["Zyloric", "Telma", "Ecosprin", "Atorva", "Thyronorm", "Montair",
             "Levocet", "Shelcal", "Rosuvas", "Glycomet", "Amlokind", "Cilacar"]
    case_id = _upload(
        monkeypatch,
        segments=[(f"Tab {n} 1-0-1", 0.3) for n in names],
        medicines=[{"name": n, "cost": 10} for n in names],
    )
    bench = _bench(case_id)
    assert len(_tasks(case_id)) == 10
    over = [r for r in bench.values() if r["trust"].get("reasons") == ["OVER_CAP"]]
    assert len(over) == 2 and all(r["benchmark"] is None for r in over)
    assert all(r["benchmark"] is None for r in bench.values()), "every uncertain medicine is blocked"


# --- 4. LLM-rewritten name ----------------------------------------------------------

def test_llm_normalised_name_is_not_trusted(monkeypatch):
    case_id = _upload(
        monkeypatch,
        segments=[("Cap Amoxycilin 500 1-1-1", 0.25)],
        medicines=[{"name": "Amoxicillin 500", "cost": 90}],
    )
    row = _bench(case_id)["Amoxicillin 500"]
    assert row["benchmark"] is None and row["trust"]["reasons"] == ["POSSIBLE_MATCH"]
    assert row["name_provenance"] == "AI_DERIVED", "a normalisation is never HUMAN_REVIEWED"

    # The patient asks for a human reading of the whole entry; two readers agree.
    entity_id = _medicine_ids(case_id)["Amoxicillin 500"]
    task_id = _flag_whole_entry(case_id, entity_id)
    _read(case_id, task_id, "Amoxycillin 500", "amoxycillin 500")
    row = _bench(case_id)["Amoxycillin 500"]
    assert row["trust"]["state"] == "HUMAN_RESOLVED" and row["name_provenance"] == "HUMAN_REVIEWED"


# --- 5. NOT_APPLIED lifecycle -------------------------------------------------------

def test_not_applied_is_blocked_and_not_erased_by_a_later_partial_reading(monkeypatch):
    case_id = _upload(
        monkeypatch,
        segments=[("Augmntn", 0.3), ("625mg", 0.35), ("1-0-1", 0.95)],
        medicines=[{"name": "Tab Augmntn 625mg", "cost": 220}],
    )
    tasks = {t["ocr_candidate"]: t for t in _tasks(case_id)}
    assert set(tasks) == {"Augmntn", "625mg"}

    # First reading of "Augmntn" names no drug ("Tab.") -> cannot be placed.
    _read(case_id, tasks["Augmntn"]["task_id"], "Tab.", "tab.")
    task = next(t for t in _tasks(case_id) if t["task_id"] == tasks["Augmntn"]["task_id"])
    assert task["status"] == "RESOLVED" and task["outcome"] == "NOT_APPLIED"
    row = _bench(case_id)["Tab Augmntn 625mg"]
    assert row["benchmark"] is None and row["transcription_status"] == "OPEN", "the other task is still open"

    # A later, valid PARTIAL reading of the strength must not settle the entry.
    _read(case_id, tasks["625mg"]["task_id"], "625mg", "625 mg")
    row = _bench(case_id)["Tab Augmntn 625mg"]
    assert row["benchmark"] is None and row["transcription_status"] == "NOT_APPLIED"
    assert row["trust"]["state"] == "READING_NOT_APPLIED"

    # Only a whole-entry reading settles it.
    entity_id = _medicine_ids(case_id)["Tab Augmntn 625mg"]
    whole = _flag_whole_entry(case_id, entity_id)
    _read(case_id, whole, "Augmentin 625", "augmentin 625")
    row = _bench(case_id)["Augmentin 625"]
    assert row["trust"]["state"] == "HUMAN_RESOLVED" and row["name_provenance"] == "HUMAN_REVIEWED"


def test_whole_entry_reading_that_is_only_a_marker_stays_not_applied(monkeypatch):
    case_id = _upload(monkeypatch, segments=[("Pan", 0.3)],
                      medicines=[{"name": "Pan 40", "cost": 120}, {"name": "Pan-D", "cost": 150}])
    entity_id = _medicine_ids(case_id)["Pan 40"]
    task_id = _flag_whole_entry(case_id, entity_id)
    _read(case_id, task_id, "Tab.", "Tab.")
    row = _bench(case_id)["Pan 40"]
    assert row["benchmark"] is None
    assert row["trust"]["state"] in ("READING_NOT_APPLIED", "OCR_UNCERTAIN")
    assert "Tab." not in _bench(case_id), "a marker never becomes a medicine name"


def test_escalated_reading_blocks_until_a_later_whole_entry_reading(monkeypatch):
    case_id = _upload(monkeypatch, segments=[("Augmntn", 0.3)],
                      medicines=[{"name": "Tab Augmntn 625mg", "cost": 220}])
    task_id = _tasks(case_id)[0]["task_id"]
    _read(case_id, task_id, "Augmentin", "Azithral")
    row = _bench(case_id)["Tab Augmntn 625mg"]
    assert row["benchmark"] is None and row["trust"]["state"] == "READERS_DISAGREED"
    whole = _flag_whole_entry(case_id, _medicine_ids(case_id)["Tab Augmntn 625mg"])
    _read(case_id, whole, "Augmentin 625", "Augmentin 625")
    assert _bench(case_id)["Augmentin 625"]["trust"]["state"] == "HUMAN_RESOLVED"


# --- evidence packets reflect the same decision --------------------------------------

def test_reviewer_evidence_marks_held_back_medicine_as_unsettled(monkeypatch):
    case_id = _upload(monkeypatch, segments=[("Pan", 0.3)],
                      medicines=[{"name": "Pan 40", "cost": 120}, {"name": "Pan-D", "cost": 150}])
    reviewer_id, token = register()
    review = client.post(f"{K}/cases/{case_id}/clinical-reviews",
                         json={"source_module": "dawacheck", "share_with_reviewer_consent": True})
    assert review.status_code == 201, review.text
    review_id = review.json()["review_id"]
    client.post(f"{K}/cases/{case_id}/clinical-reviews/{review_id}/assign", json={"reviewer_id": reviewer_id})
    client.post(f"{K}/clinical-reviews/{review_id}/accept", json={"coi_category": "INDEPENDENT_REVIEWER"}, headers=rh(token))
    items = client.get(f"{K}/clinical-reviews/{review_id}/evidence", headers=rh(token)).json()["evidence"]
    meds = [i for i in items if i["kind"] == "medicine"]
    assert meds and all("unsettled" in i["value"] and i["provenance"] == "AI_DERIVED" for i in meds)


@pytest.fixture(autouse=True)
def _restore_pipeline():
    yield
