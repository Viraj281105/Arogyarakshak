"""Regression tests for the ADR-011 audit's top issues (OCR linking, full-text safety
coverage, reviewer directory, demo lockout, safety-rule approval rounds)."""

import asyncio
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.background import get_background_session
from app.clinical.transcription_service import create_tasks_from_ocr
from app.config import settings
from app.models import KadiCase, KadiEntity, KadiSafetyScanResult
from kadi.clinical_review.transcription import OcrSegment, select_uncertain_segments
from tests.clinical_helpers import ADMIN_KEY, K, admin, client, make_case, register, rh

PRESCRIPTION = b"City Care Hospital\nDiagnosis: J02 Pharyngitis\nTab Augmntn 625mg 220\nTotal: 220\n"


@pytest.fixture
def governance(monkeypatch):
    monkeypatch.setattr(settings, "clinical_governance_admin_key", ADMIN_KEY)
    monkeypatch.setattr(settings, "safety_rule_required_approvals", 1)


def _run(fn):
    async def go():
        async with get_background_session() as s:
            return await fn(s)
    return asyncio.run(go())


# --- Issue 1: OCR tasks ------------------------------------------------------------

def _ocr_tasks(case_id):
    async def go(s):
        meds = (await s.execute(select(KadiEntity).join(KadiCase.entities).where(
            KadiCase.id == case_id, KadiEntity.type == "medicine"))).scalars().all()
        payloads = select_uncertain_segments([
            OcrSegment("CITY CARE HOSPITAL", 0.3), OcrSegment("Dr. Mehta MBBS", 0.4),
            OcrSegment("Rx", 0.2), OcrSegment("Tab.", 0.3), OcrSegment("Augmntn", 0.3),
            OcrSegment("625mg", 0.95), OcrSegment("Date 12/03/2026", 0.3),
        ])
        tasks = await create_tasks_from_ocr(s, case_id, payloads, meds)
        await s.commit()
        return [(t.id, t.ocr_candidate, t.entity_id) for t in tasks]
    return _run(go)


def test_ocr_creates_only_linked_medicine_tasks_and_substitutes_the_reading():
    case_id = make_case(PRESCRIPTION)
    tasks = _ocr_tasks(case_id)
    assert [c for _, c, _ in tasks] == ["Augmntn"], "no letterhead, prescriber, Rx, Tab. or date tasks"
    task_id, _, entity_id = tasks[0]
    assert entity_id is not None

    a_id, a = register(category="PHARMACIST", name="Pharm A")
    b_id, b = register(category="MEDICAL_TRANSCRIPTIONIST", name="Scribe B", reg=None)
    for rid in (a_id, b_id):
        client.post(f"{K}/cases/{case_id}/transcriptions/{task_id}/assign",
                    json={"reviewer_id": rid, "share_with_reviewer_consent": True})
    listed = client.get(f"{K}/cases/{case_id}/transcriptions").json()[0]
    assert "Mehta" not in listed["masked_context"]
    client.post(f"{K}/transcriptions/{task_id}/readings", json={"value": "Augmentin"}, headers=rh(a))
    client.post(f"{K}/transcriptions/{task_id}/readings", json={"value": "augmentin"}, headers=rh(b))

    bench = client.get(f"/api/v1/dawacheck/cases/{case_id}/benchmark").json()
    med = next(r for r in bench if r["entity_id"] == entity_id)
    assert med["brand_name"] == "Tab Augmentin 625mg", "only the uncertain token is replaced; strength kept"
    assert med["name_provenance"] == "HUMAN_REVIEWED"


def test_partial_field_flags_are_refused():
    case_id = make_case(PRESCRIPTION)
    med = next(e for e in client.get(f"{K}/cases/{case_id}").json()["entities"] if e["type"] == "medicine")
    res = client.post(f"{K}/cases/{case_id}/transcriptions", json={"entity_id": med["id"], "field_type": "STRENGTH"})
    assert res.status_code == 422


# --- Issue 4: safety coverage beyond the excerpt -------------------------------------

def _activate_stroke_rule():
    a_id, a = register(name="Dr. Board A")
    b_id, b = register(name="Dr. Board B")
    for rid in (a_id, b_id):
        client.post(f"{K}/clinical-reviewers/{rid}/safety-board", json={"seated": True}, headers=admin())
    rule = client.post(f"{K}/safety-rules", headers=rh(a), json={
        "rule_key": "stroke-fast", "title": "Possible stroke signs", "description": "FAST",
        "trigger": {"match_any": ["slurred speech"], "context_types": ["document_text"]},
        "action": {"type": "SHOW_SAFETY_ESCALATION", "severity": "URGENT", "message": "Seek care now."},
        "source_name": "FAST", "limitations": "FAST only.",
        "review_due_date": str(date.today() + timedelta(days=90)),
    }).json()
    client.post(f"{K}/safety-rules/{rule['rule_id']}/submit", headers=rh(a))
    client.post(f"{K}/safety-rules/{rule['rule_id']}/decisions", json={"decision": "APPROVE"}, headers=rh(b))
    client.post(f"{K}/safety-rules/{rule['rule_id']}/activate", headers=rh(a))
    return rule["rule_id"]


def test_red_flag_beyond_the_excerpt_is_still_escalated(governance):
    _activate_stroke_rule()
    filler = b"Clinical notes: routine observation recorded. " * 40  # > 1,000 characters
    case_id = make_case(b"City Care Hospital\n" + filler + b"\nPatient developed slurred speech on day 2.\n")
    body = client.get(f"{K}/cases/{case_id}/safety-escalations").json()
    assert [e["matched_terms"] for e in body["escalations"]] == [["slurred speech"]]
    assert "checked in full" in body["scope_note"]

    stored = _run(lambda s: s.execute(select(KadiSafetyScanResult).where(KadiSafetyScanResult.case_id == case_id)))
    rows = stored.scalars().all()
    assert rows and all("Patient" not in str(r.matched_terms) for r in rows), "only terms are stored, never text"

    client.delete(f"{K}/cases/{case_id}")
    left = _run(lambda s: s.execute(select(KadiSafetyScanResult).where(KadiSafetyScanResult.case_id == case_id)))
    assert left.scalars().all() == [], "scan results are erased with the case"


def test_retired_rule_scan_results_no_longer_escalate(governance):
    rule_id = _activate_stroke_rule()
    case_id = make_case(b"City Care Hospital\nPatient developed slurred speech.\n")
    a = client.get(f"{K}/safety-rules/{rule_id}").json()["proposed_by"]
    assert a is not None
    board = register(name="Dr. Retirer")
    client.post(f"{K}/clinical-reviewers/{board[0]}/safety-board", json={"seated": True}, headers=admin())
    client.post(f"{K}/safety-rules/{rule_id}/retire", json={"reason": "replaced"}, headers=rh(board[1]))
    assert client.get(f"{K}/cases/{case_id}/safety-escalations").json()["escalations"] == []


# --- Issue 8: directory & demo lockout ----------------------------------------------

def test_self_declared_reviewers_are_not_listed_but_can_be_assigned_by_id():
    rid, _ = register(name="Dr. Claims To Be Famous", reg="MMC-REAL-123")
    assert all(r["id"] != rid for r in client.get(f"{K}/clinical-reviewers").json())
    assert client.get(f"{K}/clinical-reviewers/{rid}").status_code == 200
    case_id = make_case()
    review = client.post(f"{K}/cases/{case_id}/clinical-reviews",
                         json={"source_module": "billnyay", "share_with_reviewer_consent": True}).json()
    assert client.post(f"{K}/cases/{case_id}/clinical-reviews/{review['review_id']}/assign",
                       json={"reviewer_id": rid}).status_code == 200


def test_demo_reviewers_are_listed_only_in_demo_mode_and_locked_out_otherwise(monkeypatch):
    monkeypatch.setattr(settings, "clinical_governance_admin_key", ADMIN_KEY)
    monkeypatch.setattr(settings, "clinical_demo_mode", True)
    seed = client.post(f"{K}/clinical-demo/seed", headers=admin()).json()
    demo = seed["reviewers"]["clinician_a"]
    assert any(r["id"] == demo["reviewer_id"] for r in client.get(f"{K}/clinical-reviewers").json())

    monkeypatch.setattr(settings, "clinical_demo_mode", False)
    assert all(r["id"] != demo["reviewer_id"] for r in client.get(f"{K}/clinical-reviewers").json())
    assert client.get(f"{K}/clinical-reviewers/{demo['reviewer_id']}").status_code == 404
    assert client.get(f"{K}/clinical-reviewers/me", headers=rh(demo["reviewer_token"])).status_code == 403


# --- Issue 9: approval rounds ------------------------------------------------------

def test_unchanged_resubmission_after_rejection_starts_a_fresh_round(monkeypatch):
    monkeypatch.setattr(settings, "clinical_governance_admin_key", ADMIN_KEY)
    monkeypatch.setattr(settings, "safety_rule_required_approvals", 2)
    seats = [register(name=f"Dr. Seat {i}") for i in range(3)]
    for rid, _ in seats:
        client.post(f"{K}/clinical-reviewers/{rid}/safety-board", json={"seated": True}, headers=admin())
    (_, a), (_, b), (_, c) = seats
    rule = client.post(f"{K}/safety-rules", headers=rh(a), json={
        "rule_key": "round-test", "title": "t", "description": "d",
        "trigger": {"match_any": ["seizure"]}, "action": {"type": "SHOW_SAFETY_ESCALATION", "message": "m"},
        "source_name": "s", "limitations": "l", "review_due_date": str(date.today() + timedelta(days=30)),
    }).json()
    rid = rule["rule_id"]
    client.post(f"{K}/safety-rules/{rid}/submit", headers=rh(a))
    client.post(f"{K}/safety-rules/{rid}/decisions", json={"decision": "APPROVE"}, headers=rh(b))
    client.post(f"{K}/safety-rules/{rid}/decisions", json={"decision": "REJECT", "comment": "too broad"}, headers=rh(c))

    client.post(f"{K}/safety-rules/{rid}/submit", headers=rh(a))  # unchanged content
    after_c = client.post(f"{K}/safety-rules/{rid}/decisions", json={"decision": "APPROVE"}, headers=rh(c))
    assert after_c.status_code == 200, "the reviewer who rejected can decide on the new round"
    assert after_c.json()["status"] == "UNDER_REVIEW", "B's approval from the earlier round must not count"
    final = client.post(f"{K}/safety-rules/{rid}/decisions", json={"decision": "APPROVE"}, headers=rh(b))
    assert final.json()["status"] == "APPROVED"
    assert client.post(f"{K}/safety-rules/{rid}/activate", headers=rh(a)).json()["status"] == "ACTIVE"
