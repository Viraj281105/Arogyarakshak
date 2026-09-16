"""
SEC-03 regression: server-side case expiry and automatic purge, independent of the
client ever presenting its access token again.

Before this fix, the ONLY deletion path was the client-initiated DELETE /cases/{id}
route (P1-10) — a client that lost its token had no way to ever trigger cleanup, so a
case was retained forever by default. `expires_at` is now set at creation and
`app.case_retention.sweep_expired_cases` purges expired cases on its own schedule.
"""

import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select

from app.background import get_background_session
from app.case_retention import find_expired_case_ids, sweep_expired_cases
from app.main import app
from app.models import BillNyayAppeal, KadiCase, KadiEntity, kadi_case_entities
from tests.auth_test_client import AuthAwareTestClient

client = AuthAwareTestClient(app)


def _with_session(fn):
    async def runner():
        async with get_background_session() as session:
            return await fn(session)

    return asyncio.run(runner())


def _case_with_document() -> str:
    res = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
    case_id = res.json()["id"]
    upload = client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("bill.txt", b"Consultation: 500\nTotal Amount: 500\n")},
    )
    assert upload.status_code == 202
    return case_id


def _set_expiry(case_id: str, when):
    async def _set(session):
        result = await session.execute(select(KadiCase).where(KadiCase.id == case_id))
        case = result.scalar_one()
        case.expires_at = when
        await session.commit()

    _with_session(_set)


# ---------------------------------------------------------------------------
# expires_at is set unconditionally at creation
# ---------------------------------------------------------------------------


def test_case_creation_sets_a_future_expiry():
    res = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
    case_id = res.json()["id"]

    row = _with_session(lambda s: s.execute(select(KadiCase).where(KadiCase.id == case_id)))
    case = row.scalar_one()
    assert case.expires_at is not None
    assert case.expires_at > datetime.utcnow()


# ---------------------------------------------------------------------------
# Expired cases are found and purged WITHOUT any client action / token
# ---------------------------------------------------------------------------


def test_find_expired_case_ids_includes_a_past_deadline():
    case_id = _case_with_document()
    _set_expiry(case_id, datetime.utcnow() - timedelta(days=1))

    expired = _with_session(lambda s: find_expired_case_ids(s))
    assert case_id in expired


def test_find_expired_case_ids_excludes_a_future_deadline():
    case_id = _case_with_document()
    _set_expiry(case_id, datetime.utcnow() + timedelta(days=30))

    expired = _with_session(lambda s: find_expired_case_ids(s))
    assert case_id not in expired


def test_a_case_with_no_expires_at_is_treated_as_already_expired():
    """A pre-existing row from before this column existed must default to 'purge on
    next sweep', never to 'retain forever'."""
    case_id = _case_with_document()
    _set_expiry(case_id, None)

    expired = _with_session(lambda s: find_expired_case_ids(s))
    assert case_id in expired


def test_sweep_purges_an_expired_case_with_no_client_token_presented():
    """The exact SEC-03 property: purging happens even though nothing in this test ever
    sends the case's access token anywhere near a DELETE request."""
    case_id = _case_with_document()
    appeal_res = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal")
    assert appeal_res.status_code == 200
    client.forget_token(case_id)  # simulate the client having permanently lost its token

    _set_expiry(case_id, datetime.utcnow() - timedelta(minutes=1))

    purged_count = _with_session(lambda s: sweep_expired_cases(s))
    assert purged_count >= 1

    remaining_case = _with_session(lambda s: s.execute(select(KadiCase).where(KadiCase.id == case_id)))
    assert remaining_case.scalar_one_or_none() is None

    remaining_appeal = _with_session(
        lambda s: s.execute(select(BillNyayAppeal).where(BillNyayAppeal.case_id == case_id))
    )
    assert remaining_appeal.scalar_one_or_none() is None


def test_sweep_cascades_through_derived_data_exactly_like_manual_deletion():
    case_id = _case_with_document()
    entities_before = client.get(f"/api/v1/kadi/cases/{case_id}").json()["entities"]
    assert len(entities_before) > 0
    entity_ids = [e["id"] for e in entities_before]

    _set_expiry(case_id, datetime.utcnow() - timedelta(minutes=1))
    _with_session(lambda s: sweep_expired_cases(s))

    remaining_associations = _with_session(
        lambda s: s.execute(select(kadi_case_entities.c.entity_id).where(kadi_case_entities.c.case_id == case_id))
    )
    assert remaining_associations.all() == []

    remaining_entities = _with_session(
        lambda s: s.execute(select(KadiEntity).where(KadiEntity.id.in_(entity_ids)))
    )
    assert remaining_entities.scalars().all() == []


def test_sweep_does_not_touch_a_non_expired_case():
    case_id = _case_with_document()
    _set_expiry(case_id, datetime.utcnow() + timedelta(days=30))

    _with_session(lambda s: sweep_expired_cases(s))

    assert client.get(f"/api/v1/kadi/cases/{case_id}").status_code == 200


def test_sweep_purges_multiple_expired_cases_in_one_pass():
    case_ids = [_case_with_document() for _ in range(3)]
    for cid in case_ids:
        _set_expiry(cid, datetime.utcnow() - timedelta(minutes=1))

    purged_count = _with_session(lambda s: sweep_expired_cases(s))
    assert purged_count >= 3

    for cid in case_ids:
        remaining = _with_session(lambda s: s.execute(select(KadiCase).where(KadiCase.id == cid)))
        assert remaining.scalar_one_or_none() is None
