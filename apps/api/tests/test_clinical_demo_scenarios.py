"""ADR-011 demo scenarios A-D, end to end, using the demo seed. Doubles as the executable
walkthrough script for the demo (docs/architecture/clinical-review.md)."""

import pytest

from app.config import settings
from tests.clinical_helpers import (
    ADMIN_KEY,
    FACT_CONFIRM,
    K,
    MISMATCH_DOC,
    accept,
    admin,
    assign,
    client,
    draft,
    finalize,
    make_case,
    rh,
)

STROKE_DOC = b"City Care Hospital\nDiagnosis: I63 Cerebral infarction\nBrought with slurred speech.\nCT Brain 4000\n"


@pytest.fixture
def demo(monkeypatch):
    monkeypatch.setattr(settings, "clinical_governance_admin_key", ADMIN_KEY)
    monkeypatch.setattr(settings, "clinical_demo_mode", True)
    res = client.post(f"{K}/clinical-demo/seed", headers=admin())
    assert res.status_code == 200, res.text
    return res.json()


def test_seed_is_refused_outside_demo_mode(monkeypatch):
    monkeypatch.setattr(settings, "clinical_governance_admin_key", ADMIN_KEY)
    monkeypatch.setattr(settings, "clinical_demo_mode", False)
    assert client.post(f"{K}/clinical-demo/seed", headers=admin()).status_code == 403


def test_seed_is_labelled_and_rerunnable(demo):
    assert "DEMO FIXTURES ONLY" in demo["warning"]
    a = client.get(f"{K}/clinical-reviewers/{demo['reviewers']['clinician_a']['reviewer_id']}").json()
    assert a["verification_status"] == "DEMO_VERIFIED"
    assert "not checked against any real" in a["verification_label"]
    again = client.post(f"{K}/clinical-demo/seed", headers=admin()).json()
    assert again["reviewers"]["clinician_a"]["reviewer_id"] == demo["reviewers"]["clinician_a"]["reviewer_id"]
    assert again["safety_rules_created"] == []
    assert len(client.get(f"{K}/safety-rules").json()["rules"]) == 2


def test_scenario_a_billnyay_clinical_review_into_appeal(demo):
    case_id = make_case(MISMATCH_DOC)
    plaus = client.get(f"/api/v1/billnyay/cases/{case_id}/clinical-plausibility").json()
    assert plaus["clinical_review"]["status"] == "CLINICAL_REVIEW_REQUIRED"

    review = client.post(f"{K}/cases/{case_id}/clinical-reviews", json={
        "source_module": "billnyay", "trigger": "PLAUSIBILITY_FLAG", "share_with_reviewer_consent": True,
    }).json()
    doc = demo["reviewers"]["clinician_a"]
    assign(case_id, review["review_id"], doc["reviewer_id"])
    accept(review["review_id"], doc["reviewer_token"], "HOSPITAL_AFFILIATED", "Visiting surgeon at City Care Hospital")
    sid = draft(review["review_id"], doc["reviewer_token"],
                "The records list MRI brain against an appendicitis diagnosis; the documents I reviewed do not explain the indication.")
    assert finalize(review["review_id"], sid, doc["reviewer_token"]).status_code == 200

    appeal = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal").json()
    assert appeal["human_clinical_statement_attached"] is True
    stmt = appeal["clinical_statements"][0]
    assert stmt["coi_category"] == "HOSPITAL_AFFILIATED"
    assert stmt["reviewer_snapshot"]["verification_status"] == "DEMO_VERIFIED"
    assert "Demo verification only" in appeal["clinical_annex"]


def test_scenario_b_daavisetu_readiness_and_fact_confirmation(demo):
    case_id = make_case()
    inst = {"X-Institution-Token": demo["institution"]["institution_token"]}
    body = client.post(f"/api/v1/daavisetu/cases/{case_id}/readiness", json={"playbook_id": demo["playbook_id"]}, headers=inst).json()
    items = {i["item_id"]: i for i in body["items"]}
    assert items["pb_lft_report"]["status"] == "MISSING"
    assert any("Request the missing documentation" in a for a in body["recommended_actions"])

    review = client.post(f"/api/v1/daavisetu/cases/{case_id}/readiness/clinical-confirmations",
                         json={"item_ids": ["previous_treatment_history"], "share_with_reviewer_consent": True}).json()
    doc = demo["reviewers"]["clinician_b"]
    assign(case_id, review["review_id"], doc["reviewer_id"])
    accept(review["review_id"], doc["reviewer_token"], "INDEPENDENT_REVIEWER")
    fact_id = review["facts"][0]["fact_id"]
    client.post(f"{K}/clinical-reviews/{review['review_id']}/facts/{fact_id}/decision",
                json={"decision": "CONFIRMED", "note": "Records mention prior treatment.", **FACT_CONFIRM},
                headers=rh(doc["reviewer_token"]))
    after = client.post(f"/api/v1/daavisetu/cases/{case_id}/readiness", json={}).json()
    item = next(i for i in after["items"] if i["item_id"] == "previous_treatment_history")
    assert item["status"] == "CONFIRMED_BY_REVIEWER"
    assert item["clinical_decision"]["reviewer_name"] == "Dr. Demo Clinician B"


def test_scenario_c_dawacheck_uncertain_prescription(demo):
    case_id = make_case()
    med = next(e for e in client.get(f"{K}/cases/{case_id}").json()["entities"] if e["type"] == "medicine")
    task = client.post(f"{K}/cases/{case_id}/transcriptions", json={"entity_id": med["id"], "field_type": "MEDICINE_NAME"}).json()
    pharm, scribe = demo["reviewers"]["pharmacist"], demo["reviewers"]["transcriptionist"]
    for r in (pharm, scribe):
        client.post(f"{K}/cases/{case_id}/transcriptions/{task['task_id']}/assign",
                    json={"reviewer_id": r["reviewer_id"], "share_with_reviewer_consent": True})
    client.post(f"{K}/transcriptions/{task['task_id']}/readings", json={"value": "Dolo 650"}, headers=rh(pharm["reviewer_token"]))
    mid = client.get(f"/api/v1/dawacheck/cases/{case_id}/benchmark").json()
    assert next(r for r in mid if r["entity_id"] == med["id"])["transcription_status"] == "AWAITING_SECOND_REVIEW"
    client.post(f"{K}/transcriptions/{task['task_id']}/readings", json={"value": "Dolo 650"}, headers=rh(scribe["reviewer_token"]))
    final = next(r for r in client.get(f"/api/v1/dawacheck/cases/{case_id}/benchmark").json() if r["entity_id"] == med["id"])
    assert final["name_provenance"] == "HUMAN_REVIEWED"
    task_view = client.get(f"{K}/cases/{case_id}/transcriptions").json()[0]
    assert task_view["status"] == "RESOLVED" and len(task_view["readings"]) == 2


def test_scenario_d_safety_rule_escalation(demo):
    case_id = make_case(STROKE_DOC)
    body = client.get(f"{K}/cases/{case_id}/safety-escalations").json()
    esc = body["escalations"][0]
    assert esc["rule_key"] == "demo-stroke-fast-signs"
    assert esc["rule_version"] == 1
    assert esc["source"]["name"].startswith("F.A.S.T. stroke warning-sign mnemonic")
    assert esc["human_review_recommended"] is True
    assert "decision-support floor" in esc["disclaimer"]
    review = client.post(f"{K}/cases/{case_id}/clinical-reviews", json={
        "source_module": "kadi", "trigger": "SAFETY_RULE", "share_with_reviewer_consent": True,
    }).json()
    assert any(i["kind"] == "safety_escalation" for i in review["evidence_shared"])
