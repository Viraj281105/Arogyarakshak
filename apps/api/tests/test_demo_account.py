"""The synthetic demo account (docs/DEMO_GUIDE.md): real sign-in, demo servers only."""

import pytest
from sqlalchemy import select

from app.clinical.demo_account import provision_demo_account
from app.config import settings
from app.models import KadiCase, KadiUser
from app.services.accounts import DEMO_ACCOUNT_EMAIL
from tests.account_helpers import PASSWORD, bearer_for, login, plain_client, run_db

K = "/api/v1/kadi"


@pytest.fixture
def demo(monkeypatch):
    monkeypatch.setattr(settings, "clinical_demo_mode", True)
    monkeypatch.setattr(settings, "app_env", "development")


def _provision(scenarios=("A", "D")):
    async def run(db):
        return await provision_demo_account(db, scenarios)

    return run_db(run)


def _sign_in(password):
    return login(plain_client(), DEMO_ACCOUNT_EMAIL, password, transport="bearer")


def test_provisioning_is_refused_when_demo_mode_is_off(monkeypatch):
    monkeypatch.setattr(settings, "clinical_demo_mode", False)
    with pytest.raises(PermissionError):
        _provision()


def test_provisioning_is_refused_under_a_production_profile(demo, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    with pytest.raises(PermissionError):
        _provision()


def test_the_demo_account_signs_in_and_owns_only_synthetic_cases(demo):
    result = _provision()
    assert result["email"] == DEMO_ACCOUNT_EMAIL and len(result["password"]) >= 20
    res = _sign_in(result["password"])
    assert res.status_code == 200, res.text
    user = res.json()["user"]
    assert user["is_demo"] is True and user["display_name"] == "Aarav Sharma"
    headers = {"Authorization": f"Bearer {res.json()['token']}"}
    listed = {c["id"] for c in plain_client().get(f"{K}/cases", headers=headers).json()["cases"]}
    assert listed == {c["case_id"] for c in result["cases"]}
    case = plain_client().get(f"{K}/cases/{result['cases'][0]['case_id']}", headers=headers).json()
    assert any("SYNTHETIC" in str(e).upper() for e in case["entities"])


def test_reset_rotates_the_password_and_erases_only_demo_cases(demo):
    other, _ = bearer_for()
    kept = plain_client().post(f"{K}/cases", json={"consent_opt_in": True}, headers=other).json()["id"]
    first = _provision(("A",))
    old_session = _sign_in(first["password"]).json()["token"]
    second = _provision(("A",))
    assert second["password"] != first["password"]
    assert second["cases_erased"] == 1
    assert _sign_in(first["password"]).status_code == 401
    assert plain_client().get(f"{K}/cases", headers={"Authorization": f"Bearer {old_session}"}).status_code == 401
    assert plain_client().get(f"{K}/cases/{kept}", headers=other).status_code == 200

    async def case_ids(db):
        return set((await db.execute(select(KadiCase.id))).scalars().all())

    assert run_db(case_ids) == {kept, second["cases"][0]["case_id"]}


def test_turning_demo_mode_off_closes_the_account_and_its_sessions(demo, monkeypatch):
    result = _provision(("A",))
    token = _sign_in(result["password"]).json()["token"]
    monkeypatch.setattr(settings, "clinical_demo_mode", False)
    assert _sign_in(result["password"]).status_code == 401
    assert plain_client().get(f"{K}/cases", headers={"Authorization": f"Bearer {token}"}).status_code == 401


@pytest.mark.parametrize("demo_mode", [True, False])
def test_nobody_can_register_the_demo_address(monkeypatch, demo_mode):
    monkeypatch.setattr(settings, "clinical_demo_mode", demo_mode)
    res = plain_client().post(f"{K}/auth/register", json={"email": DEMO_ACCOUNT_EMAIL, "password": PASSWORD})
    assert res.status_code == 202, "the same answer as any registration"

    async def users(db):
        return (await db.execute(select(KadiUser))).scalars().all()

    assert run_db(users) == []


def test_no_email_is_ever_sent_to_the_demo_address(demo, outbox):
    _provision(("A",))
    for path in ("password-reset/request", "verification/request"):
        assert plain_client().post(f"{K}/auth/{path}", json={"email": DEMO_ACCOUNT_EMAIL}).status_code == 202
    assert outbox == []


def test_an_ordinary_account_is_not_marked_demo():
    headers, _ = bearer_for()
    assert plain_client().get(f"{K}/auth/me", headers=headers).json()["is_demo"] is False


def test_the_demo_cases_show_the_journey_after_a_report_without_claiming_an_outcome(demo):
    result = _provision(("A", "D"))
    token = _sign_in(result["password"]).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    statuses = {}
    for case in result["cases"]:
        actions = plain_client().get(f"{K}/cases/{case['case_id']}/actions", headers=headers).json()["actions"]
        assert actions and all(a["title"].startswith("DEMO") for a in actions)
        statuses[case["scenario"]] = actions[0]["status"]
    assert statuses == {"A": "response_received", "D": "awaiting_response"}
    assert result["actions"] == 2
