"""Fixes from the independent security review of the accounts backend (ADR-026).

M1 sign-in throttle per (account, client IP) with expiring failures and an increasing
delay; L3 wrong current passwords count too; M2 atomic claim; L1 atomic single-use tokens;
L4 account deletion clears in-memory status and the account's own BimaNyay records;
L7 a dead cookie never breaks guest writes; L8 no Host-derived trusted origin in production.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.background import get_background_session
from app.config import settings
from app.main import app
from app.models import BimaNyayCase, BimaNyayGrievance, KadiCase, KadiUser
from app.services import accounts as account_service
from app.services.case_ingestion import processing_status
from tests.account_helpers import (
    PASSWORD,
    WEB_ORIGIN,
    bearer_for,
    fresh_email,
    login,
    plain_client,
    register,
    run_db,
    signed_in_web,
)

ME = "/api/v1/kadi/auth/me"
ATTACKER = ("198.51.100.7", 50000)
VICTIM = ("203.0.113.9", 50000)


def _client_at(address) -> TestClient:
    return TestClient(app, client=address)


@pytest.fixture
def throttle_settings(monkeypatch, relaxed_auth_limit):
    monkeypatch.setattr(settings, "login_free_failures", 3)
    monkeypatch.setattr(settings, "login_failure_window_minutes", 15)
    monkeypatch.setattr(settings, "login_max_delay_seconds", 900)


# ---------------------------------------------------------------------------
# M1: throttle per (account, client IP)
# ---------------------------------------------------------------------------


def test_an_attacker_cannot_lock_the_real_user_out(clock, throttle_settings):
    email = fresh_email()
    attacker, victim = _client_at(ATTACKER), _client_at(VICTIM)
    register(victim, email)
    for _ in range(50):
        assert login(attacker, email, "guessing wrong passwords").status_code == 401
    # The victim, on another network, signs in at once with the right password.
    assert login(victim, email, PASSWORD).status_code == 200


def test_throttled_attempts_look_like_any_failure_and_the_delay_grows(clock, throttle_settings):
    email = fresh_email()
    client = _client_at(ATTACKER)
    register(client, email)
    failures = [login(client, email, "wrong password here") for _ in range(3)]
    throttled = login(client, email, PASSWORD)  # correct password inside the 1 s delay
    assert throttled.status_code == 401 and throttled.json() == failures[0].json()

    clock.advance(seconds=1)
    assert login(client, email, "wrong password here").status_code == 401  # 4th failure: 2 s delay
    clock.advance(seconds=1)
    assert login(client, email, PASSWORD).status_code == 401  # still inside the 2 s delay
    clock.advance(seconds=1)
    assert login(client, email, PASSWORD).status_code == 200


def test_the_delay_is_capped(clock, monkeypatch, throttle_settings):
    monkeypatch.setattr(settings, "login_max_delay_seconds", 4)
    email = fresh_email()
    client = _client_at(ATTACKER)
    register(client, email)
    for _ in range(12):
        login(client, email, "wrong password here")
        clock.advance(seconds=5)  # always past the capped delay, so every attempt is evaluated
    login(client, email, "wrong password here")
    clock.advance(seconds=4)
    assert login(client, email, PASSWORD).status_code == 200


def test_failures_expire_after_the_window(clock, throttle_settings):
    email = fresh_email()
    client = _client_at(ATTACKER)
    register(client, email)
    for _ in range(2):
        login(client, email, "wrong password here")
    clock.advance(minutes=settings.login_failure_window_minutes, seconds=1)
    for _ in range(2):
        login(client, email, "wrong password here")
    # 4 failures in total but only 2 inside the window: below the 3 free failures.
    assert login(client, email, PASSWORD).status_code == 200


def test_a_successful_login_clears_the_failures(clock, throttle_settings):
    email = fresh_email()
    client = _client_at(ATTACKER)
    register(client, email)
    for _ in range(2):
        login(client, email, "wrong password here")
    assert login(client, email, PASSWORD).status_code == 200
    for _ in range(2):
        login(client, email, "wrong password here")
    assert login(client, email, PASSWORD).status_code == 200


# ---------------------------------------------------------------------------
# L3: wrong current passwords count toward the same throttle
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("route", ["password", "delete"])
def test_wrong_current_passwords_feed_the_throttle(route, clock, throttle_settings):
    email = fresh_email()
    client = _client_at(ATTACKER)
    register(client, email)
    headers = {"Authorization": f"Bearer {login(client, email, transport='bearer').json()['token']}"}
    for _ in range(3):
        if route == "password":
            res = client.post(
                "/api/v1/kadi/auth/password",
                json={"current_password": "not my password", "new_password": "a completely new passphrase"},
                headers=headers,
            )
        else:
            res = client.request("DELETE", ME, json={"password": "not my password"}, headers=headers)
        assert res.status_code == 403
    # The stolen session's IP is now throttled for this account, even with the right password...
    ok_body = {"current_password": PASSWORD, "new_password": "a completely new passphrase"}
    assert client.post("/api/v1/kadi/auth/password", json=ok_body, headers=headers).status_code == 403
    assert login(client, email, PASSWORD).status_code == 401
    # ...but the real user elsewhere is not.
    assert login(_client_at(VICTIM), email, PASSWORD).status_code == 200


# ---------------------------------------------------------------------------
# M2: atomic claim
# ---------------------------------------------------------------------------


def _guest_case():
    res = plain_client().post("/api/v1/kadi/cases", json={"consent_opt_in": True})
    return res.json()["id"], res.json()["access_token"]


def _user(email):
    async def q(session):
        return (await session.execute(select(KadiUser).where(KadiUser.email == email))).scalar_one()

    return run_db(q)


def _claim_with_stale_case(case_id, user, token):
    """Calls the service with a KadiCase loaded BEFORE another claim committed — what a
    concurrent request holds — so only the conditional UPDATE can stop it."""

    async def run():
        async with get_background_session() as session:
            stale = await session.get(KadiCase, case_id)
            stale.owner_user_id = None  # as it was when this request loaded it
            stale.access_token_hash = account_service.hash_token(token)
            session.expunge(stale)
            async with get_background_session() as other:
                return await account_service.claim_case(other, stale, user, token)

    return asyncio.run(run())


def test_two_claims_of_one_guest_case_have_exactly_one_winner():
    first_headers, _ = bearer_for()
    _, second_email = bearer_for()
    case_id, token = _guest_case()
    res = plain_client().post(
        f"/api/v1/kadi/cases/{case_id}/claim", headers={**first_headers, "X-Case-Access-Token": token}
    )
    assert res.json()["claimed"] is True

    with pytest.raises(account_service.CaseOwnedElsewhere):
        _claim_with_stale_case(case_id, _user(second_email), token)

    async def owner(session):
        return (await session.execute(select(KadiCase.owner_user_id).where(KadiCase.id == case_id))).scalar_one()

    first_user_id = plain_client().get(ME, headers=first_headers).json()["id"]
    assert run_db(owner) == first_user_id


def test_claim_update_needs_the_presented_token_hash_to_still_match():
    _, email = bearer_for()
    case_id, _token = _guest_case()
    with pytest.raises(account_service.CaseOwnedElsewhere):
        _claim_with_stale_case(case_id, _user(email), "not-the-token")

    async def owner(session):
        return (await session.execute(select(KadiCase.owner_user_id).where(KadiCase.id == case_id))).scalar_one()

    assert run_db(owner) is None


# ---------------------------------------------------------------------------
# L1: single-use tokens are consumed atomically
# ---------------------------------------------------------------------------


def test_an_account_token_is_consumed_exactly_once(outbox):
    client = plain_client()
    register(client, fresh_email())
    token_hash = account_service.hash_token(outbox[0].token)

    async def consume_twice():
        async with get_background_session() as session:
            now = account_service.utcnow()
            await account_service._consume_account_token_atomically(session, token_hash, "verify_email", now)
            await session.commit()
            with pytest.raises(account_service.InvalidAccountToken):
                await account_service._consume_account_token_atomically(session, token_hash, "verify_email", now)

    asyncio.run(consume_twice())
    res = client.post("/api/v1/kadi/auth/verification/confirm", json={"token": outbox[0].token})
    assert res.status_code == 400


def test_a_reset_that_lost_the_race_changes_nothing(outbox, relaxed_auth_limit, monkeypatch):
    """Simulate the concurrent winner: the token is consumed after this request looked it
    up. The loser must not set its password."""
    client = plain_client()
    email = fresh_email()
    register(client, email)
    client.post("/api/v1/kadi/auth/password-reset/request", json={"email": email})
    token = [m for m in outbox if m.purpose == "reset_password"][0].token

    real_find = account_service._find_usable_account_token

    async def find_then_lose_race(db, tok, purpose, now):
        row = await real_find(db, tok, purpose, now)
        async with get_background_session() as other:
            await account_service._consume_account_token_atomically(other, row.token_hash, purpose, now)
            await other.commit()
        return row

    monkeypatch.setattr(account_service, "_find_usable_account_token", find_then_lose_race)
    res = client.post(
        "/api/v1/kadi/auth/password-reset/confirm",
        json={"token": token, "new_password": "the losing passphrase"},
    )
    assert res.status_code == 400
    assert login(client, email, "the losing passphrase").status_code == 401
    assert login(client, email, PASSWORD).status_code == 200


# ---------------------------------------------------------------------------
# L4: deletion clears in-memory status and the account's own BimaNyay records
# ---------------------------------------------------------------------------

DENIAL_PAYLOAD = {
    "policy_number": "POL-DEL-1",
    "insurer_name": "Star Health",
    "policy_age_years": 2.0,
    "claimed_amount": 50000.0,
    "denied_or_deducted_amount": 20000.0,
    "denial_category": "PED_NON_DISCLOSURE",
    "denial_reason_raw": "Pre-existing disease not disclosed at proposal stage.",
    "diagnosis": "Type 2 diabetes mellitus",
}
TIMELINE_PAYLOAD = {"insurer_name": "Star Health", "date_initiated": "2026-01-15", "claim_number": "CLM-DEL"}


def _count(model, **filters):
    async def q(session):
        stmt = select(model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(model, key) == value)
        return len((await session.execute(stmt)).scalars().all())

    return run_db(q)


def test_account_deletion_clears_processing_status_and_owned_bimanyay_records():
    headers, _ = bearer_for()
    client = plain_client()
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}, headers=headers).json()["id"]
    processing_status[case_id] = [{"status": "upload_received", "progress": 10}]

    assert client.post("/api/v1/bimanyay/analyze", json=DENIAL_PAYLOAD, headers=headers).status_code == 200
    assert client.post("/api/v1/bimanyay/timeline", json=TIMELINE_PAYLOAD, headers=headers).status_code == 200
    assert client.post("/api/v1/bimanyay/analyze", json=DENIAL_PAYLOAD).status_code == 200  # guest record
    user_id = client.get(ME, headers=headers).json()["id"]
    assert _count(BimaNyayCase, owner_user_id=user_id) == 1
    assert _count(BimaNyayGrievance, owner_user_id=user_id) == 1

    res = client.request("DELETE", ME, json={"password": PASSWORD}, headers=headers)
    assert res.status_code == 200
    assert case_id not in processing_status
    assert _count(BimaNyayGrievance) == 0
    assert _count(BimaNyayCase) == 1  # the guest's stand-alone record is untouched


def test_case_linked_bimanyay_records_are_not_also_owner_linked():
    headers, _ = bearer_for()
    client = plain_client()
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}, headers=headers).json()["id"]
    res = client.post(f"/api/v1/bimanyay/analyze?case_id={case_id}", json=DENIAL_PAYLOAD, headers=headers)
    assert res.status_code == 200

    async def row(session):
        return (await session.execute(select(BimaNyayCase))).scalar_one()

    record = run_db(row)
    assert record.case_id == case_id and record.owner_user_id is None


# ---------------------------------------------------------------------------
# L7 / L8: Origin check
# ---------------------------------------------------------------------------


def test_a_dead_or_planted_cookie_never_breaks_a_guest_write():
    client = TestClient(app, base_url=WEB_ORIGIN)
    for value in ("garbage", "x" * 43):
        res = client.post(
            "/api/v1/kadi/cases",
            json={"consent_opt_in": True},
            headers={"Cookie": f"__Host-arogya_session={value}", "Origin": "https://evil.example"},
        )
        assert res.status_code == 201 and res.json()["owned"] is False


def test_a_revoked_cookie_is_ignored_rather_than_refused():
    web, _ = signed_in_web()
    token = web.cookies.get("__Host-arogya_session")
    web.post("/api/v1/kadi/auth/logout")
    res = TestClient(app, base_url=WEB_ORIGIN).post(
        "/api/v1/kadi/cases",
        json={"consent_opt_in": True},
        headers={"Cookie": f"__Host-arogya_session={token}"},
    )
    assert res.status_code == 201 and res.json()["owned"] is False


def test_production_does_not_trust_the_host_derived_origin(monkeypatch):
    web, _ = signed_in_web()
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "cors_origins", "https://app.example.in")
    res = web.post("/api/v1/kadi/cases", json={"consent_opt_in": True})  # Origin = the API's own
    assert res.status_code == 403
    ok = web.post("/api/v1/kadi/cases", json={"consent_opt_in": True}, headers={"Origin": "https://app.example.in"})
    assert ok.status_code == 201
    monkeypatch.setattr(settings, "auth_trusted_origins", "https://other.example.in")
    assert web.post(
        "/api/v1/kadi/cases", json={"consent_opt_in": True}, headers={"Origin": "https://app.example.in"}
    ).status_code == 403


def test_development_still_trusts_its_own_origin():
    web, _ = signed_in_web()
    assert web.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).status_code == 201

