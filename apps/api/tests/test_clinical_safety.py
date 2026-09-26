"""ADR-011 clinical safety governance: attributable, versioned, immutable rules."""

from datetime import date, timedelta

import pytest

from app.config import settings
from tests.clinical_helpers import ADMIN_KEY, K, admin, client, make_case, register, rh

STROKE_DOC = (
    b"City Care Hospital\nDiagnosis: I63 Cerebral infarction\n"
    b"Patient brought with slurred speech and facial droop.\nCT Brain 4000\n"
)


@pytest.fixture(autouse=True)
def governance(monkeypatch):
    monkeypatch.setattr(settings, "clinical_governance_admin_key", ADMIN_KEY)
    monkeypatch.setattr(settings, "safety_rule_required_approvals", 1)


def _board_member(name):
    rid, tok = register(name=name)
    assert client.post(f"{K}/clinical-reviewers/{rid}/safety-board", json={"seated": True}, headers=admin()).status_code == 200
    return rid, tok


def _rule_body(key="stroke-fast", **kw):
    body = {
        "rule_key": key,
        "title": "Possible stroke warning signs",
        "description": "Adapts FAST signs.",
        "trigger": {"match_any": ["slurred speech", "facial droop"], "context_types": ["document_text"]},
        "action": {"type": "SHOW_SAFETY_ESCALATION", "severity": "URGENT", "message": "Seek emergency care now."},
        "source_name": "FAST stroke warning signs",
        "source_version": "title reference",
        "source_section": "Warning signs",
        "limitations": "FAST signs only.",
        "effective_date": str(date.today() - timedelta(days=1)),
        "review_due_date": str(date.today() + timedelta(days=90)),
    }
    body.update(kw)
    return body


def _active_rule():
    a_id, a = _board_member("Dr. Proposer")
    b_id, b = _board_member("Dr. Approver")
    rule = client.post(f"{K}/safety-rules", json=_rule_body(), headers=rh(a)).json()
    client.post(f"{K}/safety-rules/{rule['rule_id']}/submit", headers=rh(a))
    client.post(f"{K}/safety-rules/{rule['rule_id']}/decisions", json={"decision": "APPROVE"}, headers=rh(b))
    active = client.post(f"{K}/safety-rules/{rule['rule_id']}/activate", headers=rh(a)).json()
    return active, a, b


def test_non_board_member_cannot_propose():
    _, tok = register()
    assert client.post(f"{K}/safety-rules", json=_rule_body(), headers=rh(tok)).status_code == 403


def test_board_seat_requires_doctor():
    rid, _ = register(category="PHARMACIST", name="Pharm")
    assert client.post(f"{K}/clinical-reviewers/{rid}/safety-board", json={"seated": True}, headers=admin()).status_code == 422


def test_review_due_date_and_source_are_required():
    _, a = _board_member("Dr. A")
    body = _rule_body()
    body.pop("review_due_date")
    assert client.post(f"{K}/safety-rules", json=body, headers=rh(a)).status_code == 422
    assert client.post(f"{K}/safety-rules", json=_rule_body(source_name=""), headers=rh(a)).status_code == 422


def test_proposer_cannot_approve_own_rule():
    _, a = _board_member("Dr. A")
    rule = client.post(f"{K}/safety-rules", json=_rule_body(), headers=rh(a)).json()
    client.post(f"{K}/safety-rules/{rule['rule_id']}/submit", headers=rh(a))
    res = client.post(f"{K}/safety-rules/{rule['rule_id']}/decisions", json={"decision": "APPROVE"}, headers=rh(a))
    assert res.status_code == 403


def test_cannot_activate_without_independent_approval():
    _, a = _board_member("Dr. A")
    rule = client.post(f"{K}/safety-rules", json=_rule_body(), headers=rh(a)).json()
    client.post(f"{K}/safety-rules/{rule['rule_id']}/submit", headers=rh(a))
    assert client.post(f"{K}/safety-rules/{rule['rule_id']}/activate", headers=rh(a)).status_code == 409


def test_full_lifecycle_with_attributable_approval():
    active, _, _ = _active_rule()
    assert active["status"] == "ACTIVE"
    assert active["approvals"][0]["reviewer"]["name"] == "Dr. Approver"
    assert active["approvals"][0]["decision"] == "APPROVE"
    public = client.get(f"{K}/safety-rules").json()
    assert "decision-support floor" in public["disclaimer"]
    assert [r["rule_key"] for r in public["rules"]] == ["stroke-fast"]
    events = [e["event_type"] for e in client.get(f"{K}/safety-rules/{active['rule_id']}/audit").json()]
    assert events == ["RULE_PROPOSED", "RULE_SUBMITTED", "RULE_APPROVED", "RULE_ACTIVATED"]


def test_active_rule_is_immutable_and_versioned():
    active, a, b = _active_rule()
    assert client.put(f"{K}/safety-rules/{active['rule_id']}", json=_rule_body(), headers=rh(a)).status_code == 409
    v2 = client.post(f"{K}/safety-rules/{active['rule_id']}/new-version", headers=rh(a)).json()
    assert v2["version"] == 2 and v2["status"] == "DRAFT"
    assert client.post(f"{K}/safety-rules/{active['rule_id']}/new-version", headers=rh(a)).status_code == 409
    client.put(f"{K}/safety-rules/{v2['rule_id']}", json=_rule_body(changelog="Added arm weakness",
               trigger={"match_any": ["slurred speech", "facial droop", "arm weakness"]}), headers=rh(a))
    client.post(f"{K}/safety-rules/{v2['rule_id']}/submit", headers=rh(a))
    client.post(f"{K}/safety-rules/{v2['rule_id']}/decisions", json={"decision": "APPROVE"}, headers=rh(b))
    client.post(f"{K}/safety-rules/{v2['rule_id']}/activate", headers=rh(a))
    versions = client.get(f"{K}/safety-rules/{v2['rule_id']}/versions").json()["rules"]
    assert [(r["version"], r["status"]) for r in versions] == [(1, "SUPERSEDED"), (2, "ACTIVE")]


def test_rejection_returns_to_draft_and_invalidates_approvals():
    a_id, a = _board_member("Dr. A")
    _, b = _board_member("Dr. B")
    rule = client.post(f"{K}/safety-rules", json=_rule_body(), headers=rh(a)).json()
    client.post(f"{K}/safety-rules/{rule['rule_id']}/submit", headers=rh(a))
    no_reason = client.post(f"{K}/safety-rules/{rule['rule_id']}/decisions", json={"decision": "REJECT"}, headers=rh(b))
    assert no_reason.status_code == 422, "a rejection must explain itself"
    res = client.post(f"{K}/safety-rules/{rule['rule_id']}/decisions",
                      json={"decision": "REJECT", "comment": "Trigger too broad."}, headers=rh(b))
    assert res.json()["status"] == "DRAFT"
    assert res.json()["submitted_content_sha256"] is None
    assert client.post(f"{K}/safety-rules/{rule['rule_id']}/decisions",
                       json={"decision": "APPROVE"}, headers=rh(b)).status_code == 409


def test_retirement_is_attributable():
    active, a, _ = _active_rule()
    res = client.post(f"{K}/safety-rules/{active['rule_id']}/retire", json={"reason": "Superseded by national protocol."}, headers=rh(a))
    assert res.json()["status"] == "RETIRED"
    assert client.get(f"{K}/safety-rules").json()["rules"] == []


def test_escalation_fires_with_source_version_and_disclaimer():
    _active_rule()
    case_id = make_case(STROKE_DOC)
    body = client.get(f"{K}/cases/{case_id}/safety-escalations").json()
    esc = body["escalations"][0]
    assert esc["severity"] == "URGENT"
    assert esc["rule_version"] == 1
    assert esc["source"]["name"] == "FAST stroke warning signs"
    assert set(esc["matched_terms"]) == {"slurred speech", "facial droop"}
    assert "decision-support floor" in esc["disclaimer"]
    assert esc["human_review_recommended"] is True


def test_escalations_are_not_hidden_behind_consent():
    _active_rule()
    case_id = make_case(STROKE_DOC, consent=False)
    assert client.get(f"{K}/cases/{case_id}/safety-escalations").json()["escalations"]


def test_no_rules_means_no_claim_of_safety():
    case_id = make_case(STROKE_DOC)
    body = client.get(f"{K}/cases/{case_id}/safety-escalations").json()
    assert body["escalations"] == []
    assert "not a safety assessment" in body["coverage_note"]


def test_safety_escalation_raises_plausibility_to_review():
    _active_rule()
    case_id = make_case(STROKE_DOC)
    body = client.get(f"/api/v1/billnyay/cases/{case_id}/clinical-plausibility").json()
    assert body["assessment"]["clinical_review_required"] is True
    assert body["safety_escalations"]


def test_drafts_are_not_public():
    _, a = _board_member("Dr. A")
    rule = client.post(f"{K}/safety-rules", json=_rule_body(), headers=rh(a)).json()
    assert client.get(f"{K}/safety-rules/{rule['rule_id']}").status_code == 404
    assert client.get(f"{K}/safety-rules/workspace", headers=rh(a)).json()["rules"][0]["status"] == "DRAFT"
