"""ADR-011 human OCR resolution and its DawaCheck integration."""

import asyncio

from sqlalchemy import select

from app.background import get_background_session
from app.clinical.transcription_service import create_tasks_from_ocr
from app.models import KadiCase, KadiEntity
from kadi.clinical_review.transcription import OcrSegment, select_uncertain_segments
from tests.clinical_helpers import K, client, make_case, register, rh


def _medicine(case_id):
    entities = client.get(f"{K}/cases/{case_id}").json()["entities"]
    return next(e for e in entities if e["type"] == "medicine")


def _flag(case_id, field="MEDICINE_NAME"):
    res = client.post(f"{K}/cases/{case_id}/transcriptions", json={"entity_id": _medicine(case_id)["id"], "field_type": field})
    assert res.status_code == 201, res.text
    return res.json()


def _assign(case_id, task_id, rid):
    return client.post(f"{K}/cases/{case_id}/transcriptions/{task_id}/assign",
                       json={"reviewer_id": rid, "share_with_reviewer_consent": True})


def _read(task_id, tok, value="Dolo 650", **kw):
    return client.post(f"{K}/transcriptions/{task_id}/readings", json={"value": value, **kw}, headers=rh(tok))


def _two_readers(case_id, task_id):
    a_id, a = register(category="PHARMACIST", name="Pharm A")
    b_id, b = register(category="MEDICAL_TRANSCRIPTIONIST", name="Scribe B", reg=None)
    _assign(case_id, task_id, a_id)
    _assign(case_id, task_id, b_id)
    return a, b


def test_medication_field_is_high_risk_and_needs_two_readings():
    case_id = make_case()
    task = _flag(case_id)
    assert task["risk_level"] == "HIGH" and task["required_reviews"] == 2
    a, b = _two_readers(case_id, task["task_id"])
    view = client.get(f"{K}/transcriptions/{task['task_id']}", headers=rh(a)).json()
    assert view["ocr_candidate"] is None and view["ocr_candidate_hidden"] is True, "HIGH-risk reading must be blind to OCR"
    _read(task["task_id"], a, "Dolo 650 mg")
    after_one = client.get(f"{K}/cases/{case_id}/transcriptions").json()[0]
    assert after_one["status"] == "AWAITING_SECOND_REVIEW" and after_one["final_value"] is None
    _read(task["task_id"], b, "dolo 650MG")
    done = client.get(f"{K}/cases/{case_id}/transcriptions").json()[0]
    assert done["status"] == "RESOLVED"
    assert done["final_value"] == "Dolo 650 mg"
    assert done["final_value_provenance"] == "HUMAN_REVIEWED"
    assert {r["reviewer_role"] for r in done["readings"]} == {"Pharmacist", "Medical transcriptionist"}


def test_disagreement_escalates_to_humans():
    case_id = make_case()
    task = _flag(case_id)
    a, b = _two_readers(case_id, task["task_id"])
    _read(task["task_id"], a, "Dolo 650")
    _read(task["task_id"], b, "Dolo 500")
    done = client.get(f"{K}/cases/{case_id}/transcriptions").json()[0]
    assert done["status"] == "HUMAN_ESCALATION_REQUIRED" and done["final_value"] is None


def test_unreadable_escalates():
    case_id = make_case()
    task = _flag(case_id)
    a, _ = _two_readers(case_id, task["task_id"])
    _read(task["task_id"], a, None, unreadable=True)
    assert client.get(f"{K}/cases/{case_id}/transcriptions").json()[0]["status"] == "HUMAN_ESCALATION_REQUIRED"


def test_one_reviewer_cannot_submit_twice():
    case_id = make_case()
    task = _flag(case_id)
    a, _ = _two_readers(case_id, task["task_id"])
    assert _read(task["task_id"], a).status_code == 201
    assert _read(task["task_id"], a).status_code == 409


def test_unassigned_reviewer_cannot_read_or_submit():
    case_id = make_case()
    task = _flag(case_id)
    _two_readers(case_id, task["task_id"])
    _, stranger = register(category="TRAINED_ANNOTATOR", name="Stranger", reg=None)
    assert client.get(f"{K}/transcriptions/{task['task_id']}", headers=rh(stranger)).status_code == 404
    assert _read(task["task_id"], stranger).status_code == 404


def test_cross_case_transcription_isolation():
    case_a, case_b = make_case(), make_case()
    task_a = _flag(case_a)
    task_b = _flag(case_b)
    rid, tok = register(category="PHARMACIST", name="Pharm")
    _assign(case_a, task_a["task_id"], rid)
    assert client.get(f"{K}/transcriptions/{task_b['task_id']}", headers=rh(tok)).status_code == 404
    assert client.post(f"{K}/cases/{case_b}/transcriptions/{task_a['task_id']}/assign",
                       json={"reviewer_id": rid, "share_with_reviewer_consent": True}).status_code == 404


def test_assignment_requires_consent():
    case_id = make_case()
    task = _flag(case_id)
    rid, _ = register(category="PHARMACIST", name="Pharm")
    res = client.post(f"{K}/cases/{case_id}/transcriptions/{task['task_id']}/assign", json={"reviewer_id": rid})
    assert res.status_code == 422


def test_malicious_transcription_is_bounded_and_literal():
    case_id = make_case()
    task = _flag(case_id)
    a, b = _two_readers(case_id, task["task_id"])
    assert _read(task["task_id"], a, "x" * 201).status_code == 422
    payload = "<script>alert(1)</script>\x00"
    assert _read(task["task_id"], a, payload).status_code == 201
    _read(task["task_id"], b, "<script>alert(1)</script>")
    done = client.get(f"{K}/cases/{case_id}/transcriptions").json()[0]
    assert done["final_value"] == "<script>alert(1)</script>"


def test_dawacheck_does_not_benchmark_uncertain_medicine():
    case_id = make_case()
    task = _flag(case_id)
    res = client.get(f"/api/v1/dawacheck/cases/{case_id}/benchmark").json()
    med = next(r for r in res if r["entity_id"] == task["entity_id"])
    assert med["benchmark"] is None
    assert med["transcription_status"] == "OPEN"
    assert "never treated as a medication fact" in med["note"]


def test_dawacheck_uses_human_resolved_name_with_provenance():
    case_id = make_case()
    task = _flag(case_id)
    a, b = _two_readers(case_id, task["task_id"])
    _read(task["task_id"], a, "Dolo 650")
    _read(task["task_id"], b, "Dolo 650")
    res = client.get(f"/api/v1/dawacheck/cases/{case_id}/benchmark").json()
    med = next(r for r in res if r["entity_id"] == task["entity_id"])
    assert med["brand_name"] == "Dolo 650"
    assert med["name_provenance"] == "HUMAN_REVIEWED"


def test_ocr_pipeline_creates_tasks_without_storing_images():
    case_id = make_case()

    async def run():
        async with get_background_session() as s:
            meds = (await s.execute(select(KadiEntity).join(KadiCase.entities).where(
                KadiCase.id == case_id, KadiEntity.type == "medicine"))).scalars().all()
            payloads = select_uncertain_segments([
                OcrSegment("Tab.", 0.9), OcrSegment("Dolo", 0.2, [[0, 0], [5, 0], [5, 2], [0, 2]]), OcrSegment("650mg TDS", 0.95),
            ])
            tasks = await create_tasks_from_ocr(s, case_id, payloads, meds)
            await s.commit()
            return [(t.id, t.entity_id) for t in tasks]

    created = asyncio.run(run())
    assert len(created) == 1 and created[0][1] is not None, "OCR task links to the extracted medicine"
    listed = client.get(f"{K}/cases/{case_id}/transcriptions").json()
    ocr_task = next(t for t in listed if t["source"] == "OCR_LOW_CONFIDENCE")
    assert "▢▢▢" in ocr_task["masked_context"]
    assert set(ocr_task) & {"image", "crop", "image_bytes"} == set()


def test_cancelled_task_revokes_access():
    case_id = make_case()
    task = _flag(case_id)
    a, _ = _two_readers(case_id, task["task_id"])
    client.post(f"{K}/cases/{case_id}/transcriptions/{task['task_id']}/cancel")
    assert client.get(f"{K}/transcriptions/{task['task_id']}", headers=rh(a)).status_code == 404
