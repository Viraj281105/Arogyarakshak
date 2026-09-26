"""ADR-011 DaaviSetu preauth readiness, private playbooks and clinical fact confirmation."""

import io
import re
import zipfile
from datetime import date, timedelta

from tests.clinical_helpers import FACT_CONFIRM, K, accept, assign, client, make_case, register, rh

D = "/api/v1/daavisetu"


def _institution(name="Hospital A Desk"):
    body = client.post(f"{D}/institutions", json={"name": name}).json()
    return body["institution"]["id"], {"X-Institution-Token": body["institution_token"]}


def _playbook_body(key="lap-chole", **kw):
    body = {
        "playbook_key": key,
        "title": "Lap chole checklist",
        "insurer": "Acme Health",
        "procedure_category": "Laparoscopic cholecystectomy",
        "items": [
            {"item_id": "pb_usg", "label": "USG abdomen report",
             "evidence_rule": {"kind": "document_keywords", "keywords": ["usg"]}},
            {"item_id": "pb_conservative", "label": "Documentation of conservative management tried",
             "evidence_rule": {"kind": "document_keywords", "keywords": ["conservative"]},
             "clinical_fact": True, "clinical_fact_question": "Do the records document conservative management?"},
        ],
        "commonly_requested_evidence": ["Surgeon's admission note"],
        "source_provenance": "TPA query letters 2025",
        "owner": "Desk lead",
        "effective_date": str(date.today() - timedelta(days=1)),
        "review_due_date": str(date.today() + timedelta(days=90)),
    }
    body.update(kw)
    return body


def _active_playbook(headers, **kw):
    pb = client.post(f"{D}/playbooks", json=_playbook_body(**kw), headers=headers).json()
    return client.post(f"{D}/playbooks/{pb['playbook_id']}/activate", headers=headers).json()


def test_baseline_readiness_from_case_evidence():
    case_id = make_case()
    body = client.post(f"{D}/cases/{case_id}/readiness", json={}).json()
    items = {i["item_id"]: i for i in body["items"]}
    assert items["diagnosis_documented"]["status"] == "PRESENT"
    assert items["hospital_identified"]["status"] == "PRESENT"
    assert items["investigation_reports"]["evidence_strength"] == "KEYWORD_MATCH"
    assert body["guidance_label"] == "DaaviSetu generic baseline only"
    text = str(body)
    assert "does not predict" in body["disclaimer"]
    assert not re.search(r"approval (probability|rate|chance|likelihood)", text, re.I)


def test_readiness_requires_consent():
    case_id = make_case(consent=False)
    assert client.post(f"{D}/cases/{case_id}/readiness", json={}).status_code == 403


def test_playbook_creation_versioning_and_immutability():
    _, h = _institution()
    active = _active_playbook(h)
    assert active["status"] == "ACTIVE" and active["version"] == 1
    assert "Private to this institution" in active["visibility"]
    assert client.put(f"{D}/playbooks/{active['playbook_id']}", json=_playbook_body(), headers=h).status_code == 409
    v2 = client.post(f"{D}/playbooks/{active['playbook_id']}/new-version", headers=h).json()
    assert v2["version"] == 2 and v2["status"] == "DRAFT"
    client.post(f"{D}/playbooks/{v2['playbook_id']}/activate", headers=h)
    versions = {p["version"]: p["status"] for p in client.get(f"{D}/playbooks", headers=h).json()}
    assert versions == {1: "SUPERSEDED", 2: "ACTIVE"}


def test_playbook_cannot_assert_claimant_facts():
    _, h = _institution()
    bad = _playbook_body(items=[{"item_id": "bad", "label": "Patient had failed conservative treatment",
                                 "evidence_rule": {"kind": "document_keywords", "keywords": ["x1"]}}])
    assert client.post(f"{D}/playbooks", json=bad, headers=h).status_code == 422
    bad2 = _playbook_body(commonly_requested_evidence=["Claimant was treated for 6 weeks"])
    assert client.post(f"{D}/playbooks", json=bad2, headers=h).status_code == 422


def test_playbook_from_hospital_a_never_leaks_to_hospital_b():
    _, ha = _institution("Hospital A")
    _, hb = _institution("Hospital B")
    pb_a = _active_playbook(ha)
    assert client.get(f"{D}/playbooks/{pb_a['playbook_id']}", headers=hb).status_code == 404
    assert client.get(f"{D}/playbooks", headers=hb).json() == []
    assert client.post(f"{D}/playbooks/{pb_a['playbook_id']}/retire", headers=hb).status_code == 404
    case_id = make_case()
    res = client.post(f"{D}/cases/{case_id}/readiness", json={"playbook_id": pb_a["playbook_id"]}, headers=hb)
    assert res.status_code == 404
    no_token = client.post(f"{D}/cases/{case_id}/readiness", json={"playbook_id": pb_a["playbook_id"]})
    assert no_token.status_code == 401


def test_playbook_requires_institution_credential():
    assert client.get(f"{D}/playbooks").status_code == 401
    assert client.get(f"{D}/playbooks", headers={"X-Institution-Token": "forged"}).status_code == 403


def test_expired_playbook_is_not_applied():
    _, h = _institution()
    pb = client.post(f"{D}/playbooks", json=_playbook_body(
        effective_date=str(date.today() - timedelta(days=100)),
        review_due_date=str(date.today() - timedelta(days=1))), headers=h).json()
    client.post(f"{D}/playbooks/{pb['playbook_id']}/activate", headers=h)
    case_id = make_case()
    res = client.post(f"{D}/cases/{case_id}/readiness", json={"playbook_id": pb["playbook_id"]}, headers=h)
    assert res.status_code == 409
    assert "past its review date" in res.json()["detail"]


def test_playbook_items_are_grounded_in_case_evidence():
    _, h = _institution()
    pb = _active_playbook(h)
    case_id = make_case()
    body = client.post(f"{D}/cases/{case_id}/readiness", json={"playbook_id": pb["playbook_id"]}, headers=h).json()
    items = {i["item_id"]: i for i in body["items"]}
    assert items["pb_usg"]["status"] == "PRESENT"  # "USG report" is in the document
    assert items["pb_conservative"]["status"] == "MISSING"  # never fabricated
    assert items["pb_conservative"]["origin"] == "INSTITUTION_PLAYBOOK"
    assert "Lap chole checklist (v1, Hospital A Desk)" == body["guidance_label"]


def test_clinical_fact_confirmation_flow_and_package():
    case_id = make_case()
    fact_review = client.post(f"{D}/cases/{case_id}/readiness/clinical-confirmations",
                              json={"item_ids": ["previous_treatment_history"], "share_with_reviewer_consent": True})
    assert fact_review.status_code == 201, fact_review.text
    review = fact_review.json()
    assert review["review_type"] == "FACT_CONFIRMATION"
    fact_id = review["facts"][0]["fact_id"]

    rid, tok = register()
    assign(case_id, review["review_id"], rid)
    accept(review["review_id"], tok, "TREATING_DOCTOR")
    no_confirm = client.post(f"{K}/clinical-reviews/{review['review_id']}/facts/{fact_id}/decision",
                             json={"decision": "CONFIRMED"}, headers=rh(tok))
    assert no_confirm.status_code == 422
    decided = client.post(f"{K}/clinical-reviews/{review['review_id']}/facts/{fact_id}/decision",
                          json={"decision": "REJECTED", "note": "No prior treatment is documented.", **FACT_CONFIRM},
                          headers=rh(tok))
    assert decided.status_code == 200 and decided.json()["provenance"] == "HUMAN_REVIEWED"
    again = client.post(f"{K}/clinical-reviews/{review['review_id']}/facts/{fact_id}/decision",
                        json={"decision": "CONFIRMED", **FACT_CONFIRM}, headers=rh(tok))
    assert again.status_code == 409, "decisions are immutable"

    readiness = client.post(f"{D}/cases/{case_id}/readiness", json={}).json()
    item = next(i for i in readiness["items"] if i["item_id"] == "previous_treatment_history")
    assert item["status"] == "REJECTED_BY_REVIEWER"
    assert item["clinical_decision"]["coi_label"] == "Treating doctor for this patient"

    client.post(f"{D}/cases/{case_id}/claim", json={
        "policy_number": "POL-1", "patient_name": "Test", "hospital_name": "City Care Hospital",
        "diagnosis": "K35", "treatment_plan": "Appendectomy", "estimated_cost": 45000})
    zbytes = client.get(f"{D}/cases/{case_id}/claim/package").content
    with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
        readiness_txt = zf.read("preauth_readiness.txt").decode()
        assert "[REJECTED_BY_REVIEWER] Previous treatment history" in readiness_txt
        assert "preauth_readiness.txt" in zf.read("manifest.txt").decode()


def test_confirmation_request_rejects_non_clinical_or_unknown_items():
    case_id = make_case()
    for item in ("diagnosis_documented", "made_up_fact"):
        res = client.post(f"{D}/cases/{case_id}/readiness/clinical-confirmations",
                          json={"item_ids": [item], "share_with_reviewer_consent": True})
        assert res.status_code == 422
