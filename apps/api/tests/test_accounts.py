"""User accounts: registration, sign-in, sessions, verification, reset, deletion (ADR-026).

Case ownership on the case routes is in test_case_ownership.py.
"""

import logging

import pytest
from sqlalchemy import select

from app.config import Settings, settings
from app.models import KadiAccountToken, KadiCase, KadiSession, KadiUser
from app.services import accounts as account_service
from app.services import passwords
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
    web_client,
)

ME = "/api/v1/kadi/auth/me"


def _count(model, **filters):
    async def q(session):
        stmt = select(model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(model, key) == value)
        return len((await session.execute(stmt)).scalars().all())

    return run_db(q)


# ---------------------------------------------------------------------------
# Registration and enumeration resistance
# ---------------------------------------------------------------------------


def test_register_answers_the_same_for_new_and_existing_addresses():
    client = plain_client()
    email = fresh_email()
    first = client.post("/api/v1/kadi/auth/register", json={"email": email, "password": PASSWORD})
    second = client.post("/api/v1/kadi/auth/register", json={"email": email.upper(), "password": "another long password"})
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()
    assert _count(KadiUser) == 1
    # The second attempt changed nothing: the original password still works.
    assert login(client, email).status_code == 200


def test_register_normalises_the_email():
    client = plain_client()
    register(client, "  Mixed.Case@Example.ORG ")
    assert login(client, "mixed.case@example.org").status_code == 200


@pytest.mark.parametrize("bad_email", ["no-at-sign", "a@b", "@example.org", "two@@example.org", "sp ace@example.org"])
def test_register_rejects_a_malformed_email(bad_email):
    res = plain_client().post("/api/v1/kadi/auth/register", json={"email": bad_email, "password": PASSWORD})
    assert res.status_code == 422
    assert res.json()["message"] == "Enter a valid email address."


@pytest.mark.parametrize("bad_password", ["short", " " * 20])
def test_register_enforces_the_length_based_password_policy(bad_password):
    res = plain_client().post("/api/v1/kadi/auth/register", json={"email": fresh_email(), "password": bad_password})
    assert res.status_code == 422
    assert "detail" in res.json() and "message" in res.json()


def test_password_equal_to_the_email_is_refused():
    email = "longaddress@example.org"
    res = plain_client().post("/api/v1/kadi/auth/register", json={"email": email, "password": email})
    assert res.status_code == 422


def test_validation_errors_on_auth_routes_never_echo_the_password():
    secret = "S" * 2000  # over the 1024 max_length: a schema-level validation error
    res = plain_client().post("/api/v1/kadi/auth/login", json={"email": fresh_email(), "password": secret})
    assert res.status_code == 422
    assert secret not in res.text
    assert "input" not in res.text


def test_registration_and_login_spend_one_scrypt_derivation_on_every_path(monkeypatch, relaxed_auth_limit):
    """Timing class: unknown email, wrong password, known account and a taken address all
    do the same expensive work, so response time does not reveal an account."""
    calls = []
    real = passwords._derive

    def spy(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)

    client = plain_client()
    email = fresh_email()
    register(client, email)
    monkeypatch.setattr(passwords, "_derive", spy)
    passwords._dummy_hash = None
    login(client, "nobody@example.org", PASSWORD)  # may build the dummy hash once
    warmup = len(calls)
    assert warmup in (1, 2)

    for attempt in (
        lambda: login(client, "nobody-else@example.org", PASSWORD),
        lambda: login(client, email, "wrong password entirely"),
        lambda: login(client, email, PASSWORD),
        lambda: client.post("/api/v1/kadi/auth/register", json={"email": email, "password": PASSWORD}),
        lambda: client.post("/api/v1/kadi/auth/register", json={"email": fresh_email(), "password": PASSWORD}),
    ):
        calls.clear()
        attempt()
        assert len(calls) == 1


def test_login_failures_are_indistinguishable(relaxed_auth_limit):
    client = plain_client()
    email = fresh_email()
    register(client, email)
    wrong_password = login(client, email, "wrong password here")
    unknown_email = login(client, fresh_email(), PASSWORD)
    malformed_email = login(client, "not-an-email", PASSWORD)
    assert wrong_password.status_code == unknown_email.status_code == malformed_email.status_code == 401
    assert wrong_password.json() == unknown_email.json() == malformed_email.json()


# ---------------------------------------------------------------------------
# Sessions: cookie and bearer
# ---------------------------------------------------------------------------


def test_cookie_login_sets_a_hardened_cookie_and_no_token_in_the_body():
    client = web_client()
    email = fresh_email()
    register(client, email)
    res = login(client, email)
    assert res.status_code == 200
    body = res.json()
    assert body["token"] is None
    assert body["session"]["transport"] == "cookie"
    assert body["user"]["email"] == email and body["user"]["email_verified"] is False

    cookie = res.headers["set-cookie"]
    assert cookie.startswith("__Host-arogya_session=")
    lowered = cookie.lower()
    for attribute in ("httponly", "secure", "samesite=strict", "path=/"):
        assert attribute in lowered
    assert "domain=" not in lowered

    me = client.get(ME)
    assert me.status_code == 200 and me.json()["email"] == email


def test_bearer_login_returns_the_token_once_and_sets_no_cookie():
    client = plain_client()
    email = fresh_email()
    register(client, email)
    res = login(client, email, transport="bearer")
    assert res.status_code == 200
    assert "set-cookie" not in res.headers
    token = res.json()["token"]
    assert token and len(token) >= 40
    assert client.get(ME, headers={"Authorization": f"Bearer {token}"}).json()["email"] == email
    # Only the hash is stored.
    hashes = run_db(lambda s: _all_session_hashes(s))
    assert token not in hashes and account_service.hash_token(token) in hashes


async def _all_session_hashes(session):
    return [row.token_hash for row in (await session.execute(select(KadiSession))).scalars().all()]


def test_me_requires_a_session():
    assert plain_client().get(ME).status_code == 401
    assert plain_client().get(ME, headers={"Authorization": "Bearer not-a-real-token"}).status_code == 401


def test_a_cookie_session_token_cannot_be_replayed_as_a_bearer_token():
    client, _ = signed_in_web()
    token = client.cookies.get("__Host-arogya_session")
    assert token
    assert plain_client().get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_logout_revokes_the_session_and_clears_the_cookie():
    client, _ = signed_in_web()
    token = client.cookies.get("__Host-arogya_session")
    res = client.post("/api/v1/kadi/auth/logout")
    assert res.status_code == 204
    assert "__Host-arogya_session=" in res.headers.get("set-cookie", "")
    # Even replaying the old cookie value is refused: the session row is revoked.
    replay = web_client()
    assert replay.get(ME, headers={"Cookie": f"__Host-arogya_session={token}"}).status_code == 401


def test_bearer_logout_revokes_the_token():
    headers, _ = bearer_for()
    client = plain_client()
    assert client.post("/api/v1/kadi/auth/logout", headers=headers).status_code == 204
    assert client.get(ME, headers=headers).status_code == 401


def test_idle_timeout_ends_a_session_but_activity_keeps_it_alive(clock):
    headers, _ = bearer_for()
    client = plain_client()
    idle = settings.session_idle_timeout_minutes
    clock.advance(minutes=idle - 1)
    assert client.get(ME, headers=headers).status_code == 200  # touches last_seen_at
    clock.advance(minutes=idle - 1)
    assert client.get(ME, headers=headers).status_code == 200
    clock.advance(minutes=idle + 1)
    assert client.get(ME, headers=headers).status_code == 401


def test_absolute_lifetime_ends_an_active_session(clock, monkeypatch):
    headers, _ = bearer_for()
    client = plain_client()
    step = settings.session_idle_timeout_minutes - 5
    elapsed = 0
    while elapsed + step < settings.session_lifetime_hours * 60:
        clock.advance(minutes=step)
        elapsed += step
        assert client.get(ME, headers=headers).status_code == 200
    clock.advance(minutes=step)
    assert client.get(ME, headers=headers).status_code == 401


# ---------------------------------------------------------------------------
# CSRF / Origin
# ---------------------------------------------------------------------------


def test_cookie_authenticated_writes_need_a_trusted_origin():
    client, _ = signed_in_web()
    good = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
    assert good.status_code == 201
    evil = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}, headers={"Origin": "https://evil.example"})
    assert evil.status_code == 403
    assert "trusted origin" in evil.json()["message"]
    # No Origin at all on a cookie-authenticated write is refused too.
    del client.headers["Origin"]
    assert client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).status_code == 403
    # Reads are not state-changing and stay allowed.
    assert client.get(ME).status_code == 200


def test_configured_trusted_origin_is_accepted(monkeypatch):
    monkeypatch.setattr(settings, "auth_trusted_origins", "https://app.example.in")
    client, _ = signed_in_web()
    res = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}, headers={"Origin": "https://app.example.in"})
    assert res.status_code == 201


def test_login_from_an_untrusted_browser_origin_is_refused():
    client = web_client()
    email = fresh_email()
    register(client, email)
    res = client.post(
        "/api/v1/kadi/auth/login",
        json={"email": email, "password": PASSWORD},
        headers={"Origin": "https://evil.example"},
    )
    assert res.status_code == 403


def test_bearer_requests_need_no_origin():
    headers, _ = bearer_for()
    res = plain_client().post("/api/v1/kadi/cases", json={"consent_opt_in": True}, headers=headers)
    assert res.status_code == 201


# ---------------------------------------------------------------------------
# Rate limiting and lockout
# ---------------------------------------------------------------------------


def test_auth_routes_have_a_stricter_per_ip_bucket(monkeypatch):
    monkeypatch.setattr(settings, "auth_rate_limit_per_minute", 3)
    client = plain_client()
    statuses = [login(client, fresh_email(), PASSWORD).status_code for _ in range(4)]
    assert statuses == [401, 401, 401, 429]
    limited = login(client, fresh_email(), PASSWORD)
    assert limited.status_code == 429
    assert set(limited.json()) >= {"detail", "message"}
    assert int(limited.headers["Retry-After"]) >= 1
    # The global limiter is untouched: other routes still answer.
    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/kadi/cases").status_code == 401  # answered, not rate limited


# Sign-in throttle tests (per account and client IP): test_account_hardening.py


# ---------------------------------------------------------------------------
# Password change
# ---------------------------------------------------------------------------


def test_password_change_revokes_every_session_and_rotates_the_caller():
    email = fresh_email()
    other_device, _ = bearer_for(email)
    client = plain_client()
    res = login(client, email, transport="bearer")
    mine = {"Authorization": f"Bearer {res.json()['token']}"}

    new_password = "a completely new passphrase"
    changed = client.post(
        "/api/v1/kadi/auth/password",
        json={"current_password": PASSWORD, "new_password": new_password},
        headers=mine,
    )
    assert changed.status_code == 200
    fresh = {"Authorization": f"Bearer {changed.json()['token']}"}

    assert client.get(ME, headers=mine).status_code == 401
    assert client.get(ME, headers=other_device).status_code == 401
    assert client.get(ME, headers=fresh).status_code == 200
    assert login(client, email, PASSWORD).status_code == 401
    assert login(client, email, new_password).status_code == 200


def test_password_change_needs_the_current_password():
    headers, _ = bearer_for()
    res = plain_client().post(
        "/api/v1/kadi/auth/password",
        json={"current_password": "not my password", "new_password": "a completely new passphrase"},
        headers=headers,
    )
    assert res.status_code == 403
    assert plain_client().get(ME, headers=headers).status_code == 200


def test_cookie_password_change_sets_a_new_cookie():
    client, _ = signed_in_web()
    old = client.cookies.get("__Host-arogya_session")
    res = client.post(
        "/api/v1/kadi/auth/password",
        json={"current_password": PASSWORD, "new_password": "a completely new passphrase"},
    )
    assert res.status_code == 200 and res.json()["token"] is None
    assert client.cookies.get("__Host-arogya_session") != old
    assert client.get(ME).status_code == 200


# ---------------------------------------------------------------------------
# Verification and reset (in-memory transport)
# ---------------------------------------------------------------------------


def test_registration_issues_a_single_use_verification_token(outbox):
    client = plain_client()
    email = fresh_email()
    register(client, email)
    assert [m.purpose for m in outbox] == ["verify_email"]
    assert outbox[0].to == email
    token = outbox[0].token

    assert client.post("/api/v1/kadi/auth/verification/confirm", json={"token": token}).json() == {"status": "verified"}
    headers, _ = bearer_for(email)
    assert client.get(ME, headers=headers).json()["email_verified"] is True

    again = client.post("/api/v1/kadi/auth/verification/confirm", json={"token": token})
    assert again.status_code == 400
    assert set(again.json()) == {"detail", "message"}


def test_verification_tokens_expire(outbox, clock):
    client = plain_client()
    register(client, fresh_email())
    clock.advance(hours=settings.account_verification_token_ttl_hours, minutes=1)
    res = client.post("/api/v1/kadi/auth/verification/confirm", json={"token": outbox[0].token})
    assert res.status_code == 400


def test_requesting_verification_is_uniform_and_voids_older_tokens(outbox):
    client = plain_client()
    email = fresh_email()
    register(client, email)
    known = client.post("/api/v1/kadi/auth/verification/request", json={"email": email})
    unknown = client.post("/api/v1/kadi/auth/verification/request", json={"email": fresh_email()})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(outbox) == 2  # registration + the one known request; nothing for the unknown address
    first, second = outbox
    assert client.post("/api/v1/kadi/auth/verification/confirm", json={"token": first.token}).status_code == 400
    assert client.post("/api/v1/kadi/auth/verification/confirm", json={"token": second.token}).status_code == 200


def test_password_reset_flow(outbox, relaxed_auth_limit):
    client = plain_client()
    email = fresh_email()
    headers, _ = bearer_for(email)
    known = client.post("/api/v1/kadi/auth/password-reset/request", json={"email": email})
    unknown = client.post("/api/v1/kadi/auth/password-reset/request", json={"email": fresh_email()})
    assert known.status_code == unknown.status_code == 202 and known.json() == unknown.json()
    resets = [m for m in outbox if m.purpose == "reset_password"]
    assert len(resets) == 1
    token = resets[0].token

    weak = client.post("/api/v1/kadi/auth/password-reset/confirm", json={"token": token, "new_password": "short"})
    assert weak.status_code == 422
    assert token not in weak.text

    new_password = "brand new reset passphrase"
    done = client.post("/api/v1/kadi/auth/password-reset/confirm", json={"token": token, "new_password": new_password})
    assert done.json() == {"status": "password_reset"}
    assert client.get(ME, headers=headers).status_code == 401  # every session revoked
    assert login(client, email, PASSWORD).status_code == 401
    assert login(client, email, new_password).status_code == 200
    reuse = client.post("/api/v1/kadi/auth/password-reset/confirm", json={"token": token, "new_password": "yet another passphrase"})
    assert reuse.status_code == 400


def test_password_reset_tokens_expire(outbox, clock):
    client = plain_client()
    email = fresh_email()
    register(client, email)
    client.post("/api/v1/kadi/auth/password-reset/request", json={"email": email})
    token = [m for m in outbox if m.purpose == "reset_password"][0].token
    clock.advance(minutes=settings.password_reset_token_ttl_minutes + 1)
    res = client.post("/api/v1/kadi/auth/password-reset/confirm", json={"token": token, "new_password": "brand new reset passphrase"})
    assert res.status_code == 400


def test_a_verification_token_cannot_reset_a_password(outbox):
    client = plain_client()
    register(client, fresh_email())
    token = outbox[0].token
    res = client.post("/api/v1/kadi/auth/password-reset/confirm", json={"token": token, "new_password": "brand new reset passphrase"})
    assert res.status_code == 400


def test_disabled_transport_logs_no_address_and_no_token(caplog):
    caplog.set_level(logging.INFO)
    client = plain_client()
    email = fresh_email()
    register(client, email)
    client.post("/api/v1/kadi/auth/password-reset/request", json={"email": email})
    assert _count(KadiAccountToken, purpose="reset_password") == 1  # the token exists, hashed
    stored = run_db(lambda s: _all_token_hashes(s))

    messages = [r.getMessage() for r in caplog.records]
    assert any("not delivered" in m and "reset_password" in m for m in messages)
    assert any("not delivered" in m and "verify_email" in m for m in messages)
    for message in messages:
        assert email not in message and PASSWORD not in message
        for token_hash in stored:
            assert token_hash not in message


async def _all_token_hashes(session):
    return [row.token_hash for row in (await session.execute(select(KadiAccountToken))).scalars().all()]


# ---------------------------------------------------------------------------
# Account deletion
# ---------------------------------------------------------------------------


def test_account_deletion_erases_owned_cases_sessions_and_tokens():
    headers, email = bearer_for()
    client = plain_client()
    owned = [client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}, headers=headers).json()["id"] for _ in range(2)]
    other, _ = bearer_for()
    kept = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}, headers=other).json()["id"]

    wrong = client.request("DELETE", ME, json={"password": "not my password"}, headers=headers)
    assert wrong.status_code == 403

    res = client.request("DELETE", ME, json={"password": PASSWORD}, headers=headers)
    assert res.status_code == 200
    assert res.json() == {"deleted": True, "cases_erased": 2}

    for case_id in owned:
        assert client.get(f"/api/v1/kadi/cases/{case_id}", headers=other).status_code == 404
    assert client.get(f"/api/v1/kadi/cases/{kept}", headers=other).status_code == 200
    # Only the unrelated account remains.
    assert _count(KadiUser) == 1 and _count(KadiSession) == 1
    assert _count(KadiCase) == 1
    assert client.get(ME, headers=headers).status_code == 401
    assert login(client, email).status_code == 401


def test_cookie_account_deletion_clears_the_cookie():
    client, _ = signed_in_web()
    res = client.request("DELETE", ME, json={"password": PASSWORD})
    assert res.status_code == 200
    assert "__Host-arogya_session=" in res.headers.get("set-cookie", "")


# ---------------------------------------------------------------------------
# Hashing, settings and housekeeping
# ---------------------------------------------------------------------------


def test_password_hash_format_and_unicode_normalisation():
    stored = passwords.hash_password("ｆｕｌｌｗｉｄｔｈ passphrase")
    scheme, n, r, p, salt, key = stored.split("$")
    assert scheme == "scrypt" and (int(n), int(r), int(p)) == (2**10, 8, 1)
    # NFKC: full-width letters verify as their ASCII forms.
    assert passwords.verify_password("fullwidth passphrase", stored) == (True, False)
    assert passwords.verify_password("fullwidth passphrasE", stored)[0] is False
    assert passwords.hash_password("same") != passwords.hash_password("same")  # per-user salt
    assert passwords.verify_password("x", "garbage") == (False, False)


def test_a_hash_with_old_parameters_is_upgraded_at_login(monkeypatch):
    client = plain_client()
    email = fresh_email()
    register(client, email)
    monkeypatch.setattr(settings, "password_scrypt_n", 2**11)
    assert login(client, email).status_code == 200

    async def stored(session):
        return (await session.execute(select(KadiUser.password_hash))).scalar_one()

    assert run_db(stored).split("$")[1] == str(2**11)
    assert login(client, email).status_code == 200


def test_default_scrypt_parameters_match_the_adr():
    defaults = Settings()
    assert (defaults.password_scrypt_n, defaults.password_scrypt_r, defaults.password_scrypt_p) == (2**15, 8, 3)


@pytest.mark.parametrize("n", [1000, 1])
def test_invalid_scrypt_parameters_are_refused(n):
    with pytest.raises(ValueError):
        Settings(password_scrypt_n=n)


def test_insecure_session_cookie_is_a_production_configuration_error():
    assert any("SESSION_COOKIE_SECURE" in e for e in Settings(session_cookie_secure=False).production_config_errors())
    assert not any("SESSION_COOKIE_SECURE" in e for e in Settings().production_config_errors())


def test_insecure_cookie_setting_drops_the_host_prefix(monkeypatch):
    monkeypatch.setattr(settings, "session_cookie_secure", False)
    client = plain_client()  # plain http
    email = fresh_email()
    register(client, email)
    res = login(client, email)
    cookie = res.headers["set-cookie"]
    assert cookie.startswith("arogya_session=") and "secure" not in cookie.lower()
    assert client.get(ME).status_code == 200


def test_sweep_removes_stale_sessions_and_used_tokens(clock, outbox):
    from app.case_retention import sweep_expired_account_records

    client = plain_client()
    email = fresh_email()
    register(client, email)
    client.post("/api/v1/kadi/auth/verification/confirm", json={"token": outbox[0].token})  # used
    live, _ = bearer_for(email)
    revoked, _ = bearer_for(email)
    client.post("/api/v1/kadi/auth/logout", headers=revoked)

    assert run_db(sweep_expired_account_records) == 2  # the revoked session + the used token
    assert _count(KadiSession) == 1 and _count(KadiAccountToken) == 0
    assert client.get(ME, headers=live).status_code == 200

    clock.advance(minutes=settings.session_idle_timeout_minutes + 1)
    assert run_db(sweep_expired_account_records) == 1
    assert _count(KadiSession) == 0
    assert _count(KadiUser) == 1  # accounts never expire


def test_web_origin_constant_is_the_test_server():
    # Guards the helper: cookie tests rely on https://testserver being "this API's origin".
    assert WEB_ORIGIN == "https://testserver"


def test_password_checking_routes_share_the_auth_bucket(monkeypatch):
    headers, _ = bearer_for()
    monkeypatch.setattr(settings, "auth_rate_limit_per_minute", 2)
    from app.rate_limit import limiter

    limiter.reset()
    client = plain_client()
    body = {"current_password": "not my password", "new_password": "a completely new passphrase"}
    statuses = [client.post("/api/v1/kadi/auth/password", json=body, headers=headers).status_code for _ in range(3)]
    assert statuses == [403, 403, 429]
    assert client.request("DELETE", ME, json={"password": "nope"}, headers=headers).status_code == 429
