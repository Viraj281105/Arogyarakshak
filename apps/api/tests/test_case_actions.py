"""ADR-031 action and resolution records over HTTP."""

from datetime import date, timedelta

from sqlalchemy import select

from app.models import KadiCaseAction, KadiCaseActionEvent
from app.main import app
from tests.account_helpers import other_account, run_db
from tests.auth_test_client import AuthAwareTestClient

client = AuthAwareTestClient(app)
K = "/api/v1/kadi"
TODAY = date.today()
BILL = b"City Care Hospital\nConsultation: 500\nTotal Amount: 500\n"


def _case(document=None) -> str:
    case_id = client.post(f"{K}/cases", json={"consent_opt_in": True}).json()["id"]
    if document:
        assert client.post(f"{K}/cases/{case_id}/upload", files={"file": ("bill.txt", document)}).status_code == 202
    return case_id


def _action(case_id, **extra) -> dict:
    body = {"module": "billnyay", "kind": "clarification_request", "title": "Ask about the room rent", **extra}
    res = client.post(f"{K}/cases/{case_id}/actions", json=body)
    assert res.status_code == 201, res.text
    return res.json()


def _event(case_id, action_id, status, **extra):
    return client.post(f"{K}/cases/{case_id}/actions/{action_id}/events", json={"status": status, **extra})


def test_a_new_action_is_only_planned_and_marked_as_the_users_record():
    case_id = _case()
    action = _action(case_id, finding_ref="room-rent")
    assert action["status"] == "planned"
    assert "sent" in action["allowed_next"] and "resolved" not in action["allowed_next"]
    assert [e["provenance"] for e in action["events"]] == ["user_recorded"]
    assert client.get(f"{K}/cases/{case_id}/actions").json()["actions"][0]["id"] == action["id"]


def test_the_full_journey_to_a_user_confirmed_resolution():
    case_id = _case()
    action_id = _action(case_id)["id"]
    steps = [
        ("draft_prepared", {}),
        ("sent", {"occurred_on": str(TODAY - timedelta(days=5)), "institution": "City Care billing desk", "contact_method": "email", "amount_disputed": 900}),
        ("awaiting_response", {}),
        ("response_received", {"occurred_on": str(TODAY), "note": "They will correct the bill."}),
        ("resolved", {"amount_corrected": 900}),
    ]
    for status, extra in steps:
        res = _event(case_id, action_id, status, **extra)
        assert res.status_code == 200, res.text
    final = res.json()
    assert final["status"] == "resolved" and final["amount_corrected"] == 900
    assert final["institution"] == "City Care billing desk"
    assert [e["status"] for e in final["events"]] == ["planned"] + [s for s, _ in steps]


def test_an_impossible_jump_is_refused_and_nothing_is_written():
    case_id = _case()
    action_id = _action(case_id)["id"]
    res = _event(case_id, action_id, "response_received", occurred_on=str(TODAY))
    assert res.status_code == 409 and "can only become" in res.json()["detail"]
    stored = client.get(f"{K}/cases/{case_id}/actions").json()["actions"][0]
    assert stored["status"] == "planned" and len(stored["events"]) == 1


def test_submitted_is_not_a_status_that_exists():
    case_id = _case()
    action_id = _action(case_id)["id"]
    assert _event(case_id, action_id, "submitted").status_code == 422


def test_dates_are_required_and_cannot_be_in_the_future():
    case_id = _case()
    action_id = _action(case_id)["id"]
    assert _event(case_id, action_id, "sent").status_code == 409
    assert _event(case_id, action_id, "sent", occurred_on=str(TODAY + timedelta(days=30))).status_code == 409


def test_direct_identifiers_are_removed_before_storage():
    case_id = _case()
    action = _action(case_id, title="Call 9876543210 about the bill", institution="City Care")
    assert "9876543210" not in action["title"]
    res = _event(case_id, action["id"], "sent", occurred_on=str(TODAY), note="Mailed asha.rao@example.com, Aadhaar 1234 5678 9012")
    note = res.json()["events"][-1]["note"]
    assert "asha.rao@example.com" not in note and "1234 5678 9012" not in note


def test_supporting_evidence_must_be_a_document_of_this_case():
    case_a, case_b = _case(BILL), _case(b"Pharmacy\nTotal: 80\n")
    digest_a = client.get(f"{K}/cases/{case_a}/timeline")
    assert digest_a.status_code == 200
    import hashlib

    own = hashlib.sha256(BILL).hexdigest()
    foreign = hashlib.sha256(b"Pharmacy\nTotal: 80\n").hexdigest()
    action_id = _action(case_a)["id"]
    refused = _event(case_a, action_id, "sent", occurred_on=str(TODAY), evidence_sha256=foreign)
    assert refused.status_code == 409 and "not part of this case" in refused.json()["detail"]
    ok = _event(case_a, action_id, "sent", occurred_on=str(TODAY), evidence_sha256=own)
    assert ok.status_code == 200 and ok.json()["events"][-1]["evidence_sha256"] == own
    assert case_b != case_a


def test_unknown_fields_such_as_provenance_cannot_be_set_by_a_client():
    case_id = _case()
    action_id = _action(case_id)["id"]
    res = _event(case_id, action_id, "draft_prepared", provenance="verified")
    assert res.status_code == 422


def test_another_account_cannot_read_or_change_the_actions():
    case_id = _case()
    action_id = _action(case_id)["id"]
    intruder = other_account()
    base = f"{K}/cases/{case_id}/actions"
    assert client.get(base, headers=intruder).status_code == 403
    assert client.post(base, headers=intruder, json={"module": "billnyay", "kind": "other", "title": "x"}).status_code == 403
    assert client.post(f"{base}/{action_id}/events", headers=intruder, json={"status": "closed"}).status_code == 403
    assert client.delete(f"{base}/{action_id}", headers=intruder).status_code == 403


def test_an_action_is_reachable_only_through_its_own_case():
    case_a, case_b = _case(), _case()
    action_id = _action(case_a)["id"]
    assert _event(case_b, action_id, "closed").status_code == 404
    assert client.delete(f"{K}/cases/{case_b}/actions/{action_id}").status_code == 404


def _rows(case_id):
    async def read(db):
        actions = (await db.execute(select(KadiCaseAction).where(KadiCaseAction.case_id == case_id))).scalars().all()
        events = (await db.execute(select(KadiCaseActionEvent).where(KadiCaseActionEvent.case_id == case_id))).scalars().all()
        return len(actions), len(events)

    return run_db(read)


def test_deleting_an_action_or_the_case_erases_the_records():
    case_id = _case()
    first = _action(case_id)["id"]
    _action(case_id)
    assert client.delete(f"{K}/cases/{case_id}/actions/{first}").status_code == 204
    assert _rows(case_id) == (1, 1)
    assert client.delete(f"{K}/cases/{case_id}").status_code == 204
    assert _rows(case_id) == (0, 0)


def test_a_case_cannot_collect_unlimited_actions(monkeypatch):
    from app.services import case_actions

    monkeypatch.setattr(case_actions, "MAX_ACTIONS_PER_CASE", 2)
    case_id = _case()
    _action(case_id)
    _action(case_id)
    res = client.post(f"{K}/cases/{case_id}/actions", json={"module": "kadi", "kind": "other", "title": "third"})
    assert res.status_code == 409
