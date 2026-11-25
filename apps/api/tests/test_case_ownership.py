"""Case ownership on every case route (ADR-026 section 6), and the guest flow beside it.

The sweep below finds EVERY route whose dependency tree contains
``app.case_auth.require_case_access`` (so a new case route is covered automatically) and
checks the four callers ADR-026 names: owner, another account, a case token alone, and
nobody. Bodies are omitted on purpose: authorisation runs before body validation, so a
denied caller gets 401/403, never 422.
"""

import re
from datetime import timedelta

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import select

from app.account_auth import SIGN_IN_REQUIRED_DETAIL
from app.case_auth import (
    OTHER_ACCOUNT_DETAIL,
    UNCLAIMED_CASE_DETAIL,
    require_case_access,
    require_claimable_case,
)
from app.main import app
from app.models import KadiCase
from app.services.case_ingestion import create_case_record
from tests.account_helpers import (
    bearer_for,
    plain_client,
    run_db,
    signed_in_web,
)

OWNERSHIP_DETAILS = {OTHER_ACCOUNT_DETAIL, UNCLAIMED_CASE_DETAIL}


def _uses_case_access(dependant) -> bool:
    case_rules = (require_case_access, require_claimable_case)
    return any(d.call in case_rules or _uses_case_access(d) for d in dependant.dependencies)


def _all_api_routes():
    """(full path, methods, dependant) for every APIRoute, including those in included
    routers (FastAPI 0.148 keeps them behind _IncludedRouter with effective contexts)."""
    for route in app.routes:
        if isinstance(route, APIRoute):
            yield route.path, route.methods, route.dependant
        contexts = getattr(route, "effective_route_contexts", None)
        if contexts is None:
            continue
        for ctx in contexts() if callable(contexts) else contexts:
            if isinstance(ctx.original_route, APIRoute):
                yield ctx.path, ctx.methods, ctx.original_route.dependant


CASE_ROUTES = sorted(
    {
        (method, path)
        for path, methods, dependant in _all_api_routes()
        if _uses_case_access(dependant)
        for method in methods
    }
)


def _url(path: str, case_id: str) -> str:
    return re.sub(r"\{[^}]+\}", "x", path.replace("{case_id}", case_id))


def _guest_case():
    """A case created before sign-in became mandatory: unowned, opened once by a token."""

    async def create(db):
        case, token = await create_case_record(db, consent_opt_in=True)
        return case.id, token

    return run_db(create)


def _owned_case(headers):
    res = plain_client().post("/api/v1/kadi/cases", json={"consent_opt_in": True}, headers=headers)
    assert res.status_code == 201
    body = res.json()
    assert body["owned"] is True and body["access_token"] is None
    return body["id"]


def _claimed_case(headers):
    """An owned case that once had a case token (claimed from guest), and that token."""
    case_id, token = _guest_case()
    res = plain_client().post(
        f"/api/v1/kadi/cases/{case_id}/claim", headers={**headers, "X-Case-Access-Token": token}
    )
    assert res.status_code == 200
    return case_id, token


def test_the_sweep_covers_the_case_routes_of_every_module():
    paths = {p for _, p in CASE_ROUTES}
    assert len(CASE_ROUTES) >= 40
    for prefix in ("/kadi/", "/billnyay/", "/daavisetu/", "/schemesetu/", "/dawacheck/", "/bimanyay/"):
        assert any(prefix in p for p in paths), prefix
    assert ("POST", "/api/v1/kadi/cases/{case_id}/claim") in CASE_ROUTES


@pytest.mark.parametrize("method,path", CASE_ROUTES)
def test_owned_case_denies_everyone_but_its_owner(method, path):
    owner, _ = bearer_for()
    stranger, _ = bearer_for()
    case_id, old_token = _claimed_case(owner)
    url = _url(path, case_id)
    client = plain_client()

    nobody = client.request(method, url)
    assert nobody.status_code == 401, nobody.text
    assert nobody.json()["detail"] == SIGN_IN_REQUIRED_DETAIL

    other = client.request(method, url, headers=stranger)
    assert other.status_code == 403, other.text
    assert other.json()["detail"] == OTHER_ACCOUNT_DETAIL

    by_token = client.request(method, url, headers={"X-Case-Access-Token": old_token})
    assert by_token.status_code == 401, by_token.text

    if path.endswith("/stream"):
        return  # an allowed SSE request streams until timeout; covered separately below
    allowed = client.request(method, url, headers=owner)
    assert allowed.status_code != 401, allowed.text
    if allowed.status_code == 403:
        assert allowed.json().get("detail") not in OWNERSHIP_DETAILS, allowed.text


def test_owner_reads_the_case_and_its_stream_with_a_session(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "sse_timeout_seconds", 1)
    owner, _ = bearer_for()
    case_id = _owned_case(owner)
    client = plain_client()
    res = client.get(f"/api/v1/kadi/cases/{case_id}", headers=owner)
    assert res.status_code == 200 and case_id in res.text
    assert client.get(f"/api/v1/kadi/cases/{case_id}/stream", headers=owner).status_code == 200


def test_owned_case_with_a_web_cookie_session():
    web, _ = signed_in_web()
    res = web.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
    assert res.status_code == 201 and res.json()["owned"] is True and res.json()["access_token"] is None
    case_id = res.json()["id"]
    assert web.get(f"/api/v1/kadi/cases/{case_id}").status_code == 200
    assert plain_client().get(f"/api/v1/kadi/cases/{case_id}").status_code == 401
    assert web.delete(f"/api/v1/kadi/cases/{case_id}").status_code in (200, 204)


# ---------------------------------------------------------------------------
# Cases from before mandatory sign-in
# ---------------------------------------------------------------------------


def test_an_unclaimed_case_is_closed_even_with_its_token():
    case_id, token = _guest_case()
    headers, _ = bearer_for()
    client = plain_client()
    res = client.get(f"/api/v1/kadi/cases/{case_id}", headers={**headers, "X-Case-Access-Token": token})
    assert res.status_code == 403 and res.json()["detail"] == UNCLAIMED_CASE_DETAIL
    assert client.get("/api/v1/kadi/cases", headers=headers).json() == {"cases": []}


# ---------------------------------------------------------------------------
# Claiming
# ---------------------------------------------------------------------------


def test_claim_moves_a_guest_case_into_the_account_and_disables_its_token():
    headers, _ = bearer_for()
    case_id, token = _guest_case()
    client = plain_client()
    res = client.post(f"/api/v1/kadi/cases/{case_id}/claim", headers={**headers, "X-Case-Access-Token": token})
    assert res.json() == {"id": case_id, "owned": True, "claimed": True}
    assert client.get(f"/api/v1/kadi/cases/{case_id}", headers={"X-Case-Access-Token": token}).status_code == 401
    assert client.get(f"/api/v1/kadi/cases/{case_id}", headers=headers).status_code == 200

    async def token_hash(session):
        return (await session.execute(select(KadiCase.access_token_hash).where(KadiCase.id == case_id))).scalar_one()

    assert run_db(token_hash) is None
    again = client.post(f"/api/v1/kadi/cases/{case_id}/claim", headers=headers)
    assert again.json() == {"id": case_id, "owned": True, "claimed": False}


def test_claim_needs_both_the_session_and_the_case_token():
    headers, _ = bearer_for()
    case_id, token = _guest_case()
    client = plain_client()
    assert client.post(f"/api/v1/kadi/cases/{case_id}/claim", headers=headers).status_code == 401
    assert client.post(f"/api/v1/kadi/cases/{case_id}/claim", headers={**headers, "X-Case-Access-Token": "wrong"}).status_code == 403
    assert client.post(f"/api/v1/kadi/cases/{case_id}/claim", headers={"X-Case-Access-Token": token}).status_code == 401
    assert client.post("/api/v1/kadi/cases/no-such-case/claim", headers=headers).status_code == 404


def test_a_claimed_case_cannot_be_claimed_by_someone_else():
    owner, _ = bearer_for()
    thief, _ = bearer_for()
    case_id, token = _claimed_case(owner)
    res = plain_client().post(
        f"/api/v1/kadi/cases/{case_id}/claim", headers={**thief, "X-Case-Access-Token": token}
    )
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# GET /cases
# ---------------------------------------------------------------------------


def test_case_list_is_scoped_to_the_account_and_never_carries_tokens():
    alice, _ = bearer_for()
    bob, _ = bearer_for()
    mine = [_owned_case(alice) for _ in range(2)]
    claimed, guest_token = _claimed_case(alice)
    _owned_case(bob)
    _guest_case()

    res = plain_client().get("/api/v1/kadi/cases", headers=alice)
    assert res.status_code == 200
    listed = [c["id"] for c in res.json()["cases"]]
    assert sorted(listed) == sorted(mine + [claimed])
    assert "token" not in res.text and guest_token not in res.text
    assert set(res.json()["cases"][0]) == {
        "id", "status", "consent_opt_in", "total_charged", "created_at", "updated_at", "expires_at",
    }
    assert plain_client().get("/api/v1/kadi/cases").status_code == 401


def test_case_list_shows_only_live_cases(clock, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "session_idle_timeout_minutes", 10**7)
    monkeypatch.setattr(settings, "session_lifetime_hours", 10**6)
    headers, _ = bearer_for()
    case_id = _owned_case(headers)
    assert [c["id"] for c in plain_client().get("/api/v1/kadi/cases", headers=headers).json()["cases"]] == [case_id]
    clock.advance(days=settings.case_ttl_days, hours=1)
    assert plain_client().get("/api/v1/kadi/cases", headers=headers).json() == {"cases": []}


def test_owned_cases_still_expire_and_are_purged_by_the_sweep():
    from app.case_retention import sweep_expired_cases

    headers, _ = bearer_for()
    case_id = _owned_case(headers)

    async def expire(session):
        case = await session.get(KadiCase, case_id)
        case.expires_at = case.created_at - timedelta(days=1)
        await session.commit()

    run_db(expire)
    assert run_db(sweep_expired_cases) == 1
    assert plain_client().get(f"/api/v1/kadi/cases/{case_id}", headers=headers).status_code == 404


# ---------------------------------------------------------------------------
# BimaNyay's optional case link uses the same rule
# ---------------------------------------------------------------------------

DENIAL_PAYLOAD = {
    "policy_number": "POL-OWN-1",
    "insurer_name": "Star Health",
    "policy_age_years": 2.0,
    "claimed_amount": 50000.0,
    "denied_or_deducted_amount": 20000.0,
    "denial_category": "PED_NON_DISCLOSURE",
    "denial_reason_raw": "Pre-existing disease not disclosed at proposal stage.",
    "diagnosis": "Type 2 diabetes mellitus",
}


def test_bimanyay_case_link_follows_ownership():
    owner, _ = bearer_for()
    stranger, _ = bearer_for()
    case_id, old_token = _claimed_case(owner)
    client = plain_client()
    url = f"/api/v1/bimanyay/analyze?case_id={case_id}"
    assert client.post(url, json=DENIAL_PAYLOAD).status_code == 401
    assert client.post(url, json=DENIAL_PAYLOAD, headers={"X-Case-Access-Token": old_token}).status_code == 401
    assert client.post(url, json=DENIAL_PAYLOAD, headers=stranger).status_code == 403
    assert client.post(url, json=DENIAL_PAYLOAD, headers=owner).status_code == 200
