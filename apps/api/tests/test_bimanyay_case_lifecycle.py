"""
SEC-04 regression: BimaNyay dispute/grievance records must respect the same case-scoped
authorization and lifecycle as every other module when explicitly linked to a case, and
must be deleted/purged along with that case.

BimaNyay's own screen has no case-creation flow, so stand-alone use (no case_id
supplied) must keep working exactly as before — this is opt-in hardening for records a
caller chooses to link to a case, not a breaking change to the existing feature.
"""

import asyncio

from sqlalchemy import select

from app.background import get_background_session
from app.main import app
from app.models import BimaNyayCase, BimaNyayGrievance
from tests.auth_test_client import AuthAwareTestClient

client = AuthAwareTestClient(app)

DENIAL_PAYLOAD = {
    "policy_number": "POL-BN-1",
    "insurer_name": "Star Health",
    "policy_age_years": 2.0,
    "claimed_amount": 50000.0,
    "denied_or_deducted_amount": 20000.0,
    "denial_category": "PED_NON_DISCLOSURE",
    "denial_reason_raw": "Pre-existing disease not disclosed at proposal stage.",
    "diagnosis": "Type 2 diabetes mellitus",
}

TIMELINE_PAYLOAD = {
    "insurer_name": "Star Health",
    "date_initiated": "2026-01-15",
    "claim_number": "CLM-1",
    "current_tier": "LEVEL_1_GRO",
}


def _with_session(fn):
    async def runner():
        async with get_background_session() as session:
            return await fn(session)

    return asyncio.run(runner())


def _case() -> "tuple[str, str]":
    res = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
    return res.json()["id"], res.json()["access_token"]


# ---------------------------------------------------------------------------
# Stand-alone use (no case_id) keeps working unchanged — preserve existing behavior.
# ---------------------------------------------------------------------------


def test_analyze_without_case_id_still_works_standalone():
    res = client.post("/api/v1/bimanyay/analyze", json=DENIAL_PAYLOAD)
    assert res.status_code == 200


def test_timeline_without_case_id_still_works_standalone():
    res = client.post("/api/v1/bimanyay/timeline", json=TIMELINE_PAYLOAD)
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# Cross-case authorization: a case_id requires that case's real access token.
# ---------------------------------------------------------------------------


def test_analyze_with_case_id_requires_a_token():
    case_id, _token = _case()
    res = client.post(f"/api/v1/bimanyay/analyze?case_id={case_id}", json=DENIAL_PAYLOAD)
    assert res.status_code == 403


def test_analyze_with_case_id_rejects_a_foreign_case_token():
    case_a, _token_a = _case()
    _case_b, token_b = _case()

    res = client.post(
        f"/api/v1/bimanyay/analyze?case_id={case_a}",
        json=DENIAL_PAYLOAD,
        headers={"X-Case-Access-Token": token_b},
    )
    assert res.status_code == 403


def test_analyze_with_case_id_and_the_real_token_succeeds():
    case_id, token = _case()
    res = client.post(
        f"/api/v1/bimanyay/analyze?case_id={case_id}",
        json=DENIAL_PAYLOAD,
        headers={"X-Case-Access-Token": token},
    )
    assert res.status_code == 200


def test_analyze_with_case_id_requires_consent():
    res = client.post("/api/v1/kadi/cases", json={"consent_opt_in": False})
    case_id, token = res.json()["id"], res.json()["access_token"]

    res = client.post(
        f"/api/v1/bimanyay/analyze?case_id={case_id}",
        json=DENIAL_PAYLOAD,
        headers={"X-Case-Access-Token": token},
    )
    assert res.status_code == 403
    assert "consent" in res.json()["detail"].lower()


def test_analyze_with_a_nonexistent_case_id_returns_404():
    res = client.post(
        "/api/v1/bimanyay/analyze?case_id=CASE-doesnotexist12",
        json=DENIAL_PAYLOAD,
        headers={"X-Case-Access-Token": "anything"},
    )
    assert res.status_code == 404


def test_timeline_with_case_id_requires_a_token():
    case_id, _token = _case()
    res = client.post(f"/api/v1/bimanyay/timeline?case_id={case_id}", json=TIMELINE_PAYLOAD)
    assert res.status_code == 403


def test_timeline_with_case_id_and_the_real_token_succeeds():
    case_id, token = _case()
    res = client.post(
        f"/api/v1/bimanyay/timeline?case_id={case_id}",
        json=TIMELINE_PAYLOAD,
        headers={"X-Case-Access-Token": token},
    )
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# Records are actually linked to the case, and deleted with it.
# ---------------------------------------------------------------------------


def test_linked_record_carries_the_case_id_in_the_database():
    case_id, token = _case()
    client.post(
        f"/api/v1/bimanyay/analyze?case_id={case_id}",
        json=DENIAL_PAYLOAD,
        headers={"X-Case-Access-Token": token},
    )
    row = _with_session(
        lambda s: s.execute(select(BimaNyayCase).where(BimaNyayCase.case_id == case_id))
    )
    assert row.scalar_one_or_none() is not None


def test_standalone_record_has_no_case_id():
    client.post("/api/v1/bimanyay/analyze", json=DENIAL_PAYLOAD)
    row = _with_session(
        lambda s: s.execute(
            select(BimaNyayCase).where(BimaNyayCase.policy_number == DENIAL_PAYLOAD["policy_number"])
        )
    )
    records = row.scalars().all()
    assert any(r.case_id is None for r in records)


def test_deleting_the_case_purges_its_linked_bimanyay_record():
    case_id, token = _case()
    client.post(
        f"/api/v1/bimanyay/analyze?case_id={case_id}",
        json=DENIAL_PAYLOAD,
        headers={"X-Case-Access-Token": token},
    )
    client.post(
        f"/api/v1/bimanyay/timeline?case_id={case_id}",
        json=TIMELINE_PAYLOAD,
        headers={"X-Case-Access-Token": token},
    )

    res = client.delete(f"/api/v1/kadi/cases/{case_id}")
    assert res.status_code == 204

    remaining_case_records = _with_session(
        lambda s: s.execute(select(BimaNyayCase).where(BimaNyayCase.case_id == case_id))
    )
    assert remaining_case_records.scalars().all() == []

    remaining_grievances = _with_session(
        lambda s: s.execute(select(BimaNyayGrievance).where(BimaNyayGrievance.case_id == case_id))
    )
    assert remaining_grievances.scalars().all() == []


def test_deleting_a_case_does_not_touch_an_unrelated_standalone_bimanyay_record():
    """Deleting a case must never reach into stand-alone (case_id=None) records."""
    client.post("/api/v1/bimanyay/analyze", json=DENIAL_PAYLOAD)
    standalone_before = _with_session(
        lambda s: s.execute(select(BimaNyayCase).where(BimaNyayCase.case_id.is_(None)))
    )
    count_before = len(standalone_before.scalars().all())

    case_id, token = _case()
    client.post(
        f"/api/v1/bimanyay/analyze?case_id={case_id}",
        json=DENIAL_PAYLOAD,
        headers={"X-Case-Access-Token": token},
    )
    client.delete(f"/api/v1/kadi/cases/{case_id}")

    standalone_after = _with_session(
        lambda s: s.execute(select(BimaNyayCase).where(BimaNyayCase.case_id.is_(None)))
    )
    assert len(standalone_after.scalars().all()) == count_before
