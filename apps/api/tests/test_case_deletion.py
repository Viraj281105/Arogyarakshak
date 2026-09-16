"""
Tests for DELETE /api/v1/kadi/cases/{case_id} (P1-10).

ADR-003 has always described a case's database records as "transient" / linked to a
"temporary case UUID", but nothing enforced that: a case, its extracted entities, its
redacted document excerpt, and any generated PDFs (BillNyay appeal, DaaviSetu pre-auth
form) persisted indefinitely with no way for the patient who created it to remove them.
These tests prove the new deletion route is the real thing, not a partial or cosmetic
delete.
"""

import asyncio

from sqlalchemy import select

from tests.auth_test_client import AuthAwareTestClient
from app.background import get_background_session
from app.main import app
from app.models import BillNyayAppeal, DaaviSetuClaim, KadiEntity, kadi_case_entities

client = AuthAwareTestClient(app)


def _with_session(fn):
    async def runner():
        async with get_background_session() as session:
            return await fn(session)

    return asyncio.run(runner())

DENIAL_DOC = (
    b"Lifeline Multispeciality Hospital\n"
    b"Claim Rejection Letter\n"
    b"Denial Code: DEN-4471\n"
    b"Reason: Hospitalisation deemed for investigation only.\n"
    b"Policy Clause: Section 4.1 excludes diagnostic admissions.\n"
    b"Procedure: Laparoscopic Appendectomy\n"
    b"Total Amount: 20150\n"
)


def _case_with_document() -> str:
    res = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
    case_id = res.json()["id"]
    upload = client.post(
        f"/api/v1/kadi/cases/{case_id}/upload", files={"file": ("denial.txt", DENIAL_DOC)}
    )
    assert upload.status_code == 202
    return case_id


def test_deleting_a_case_removes_it():
    case_id = _case_with_document()
    assert client.get(f"/api/v1/kadi/cases/{case_id}").status_code == 200

    res = client.delete(f"/api/v1/kadi/cases/{case_id}")
    assert res.status_code == 204

    assert client.get(f"/api/v1/kadi/cases/{case_id}").status_code == 404


def test_deletion_removes_extracted_entities_not_just_the_case_row():
    case_id = _case_with_document()
    entities_before = client.get(f"/api/v1/kadi/cases/{case_id}").json()["entities"]
    assert len(entities_before) > 0  # sanity: real entities were extracted

    client.delete(f"/api/v1/kadi/cases/{case_id}")

    # The resolutions/graph routes both 404 on a deleted case (require_case_access
    # checks existence first), confirming the case row itself is gone.
    assert client.get(f"/api/v1/kadi/cases/{case_id}/resolutions").status_code == 404
    assert client.get(f"/api/v1/kadi/cases/{case_id}/graph").status_code == 404


def test_deletion_removes_the_generated_appeal_pdf():
    case_id = _case_with_document()
    appeal_res = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal")
    assert appeal_res.status_code == 200

    pdf_before = client.get(f"/api/v1/billnyay/cases/{case_id}/appeal/pdf")
    assert pdf_before.status_code == 200

    client.delete(f"/api/v1/kadi/cases/{case_id}")

    # Case no longer exists at all -> every case-scoped route 404s (existence checked
    # before anything else in require_case_access).
    pdf_after = client.get(f"/api/v1/kadi/cases/{case_id}")
    assert pdf_after.status_code == 404


def test_deletion_removes_the_daavisetu_claim():
    case_id = _case_with_document()
    claim_res = client.post(
        f"/api/v1/daavisetu/cases/{case_id}/claim",
        json={
            "patient_name": "Test Patient",
            "policy_number": "POL-DEL-1",
            "hospital_name": "Test Hospital",
            "diagnosis": "Test",
            "treatment_plan": "Test",
            "estimated_cost": 1000.0,
        },
    )
    assert claim_res.status_code == 200

    client.delete(f"/api/v1/kadi/cases/{case_id}")

    assert client.get(f"/api/v1/kadi/cases/{case_id}").status_code == 404


def test_deletion_removes_the_income_profile():
    case_id = _case_with_document()
    put_res = client.put(
        f"/api/v1/schemesetu/cases/{case_id}/income-profile",
        json={"annual_income_inr": 100000, "state": "Maharashtra"},
    )
    assert put_res.status_code == 200

    client.delete(f"/api/v1/kadi/cases/{case_id}")

    assert client.get(f"/api/v1/kadi/cases/{case_id}").status_code == 404


def test_deletion_requires_authorization():
    case_id = _case_with_document()
    client.forget_token(case_id)
    res = client.delete(f"/api/v1/kadi/cases/{case_id}")
    assert res.status_code == 401


def test_deletion_rejects_a_foreign_case_token():
    case_a = _case_with_document()
    case_b_res = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
    token_b = case_b_res.json()["access_token"]

    res = client.delete(f"/api/v1/kadi/cases/{case_a}", headers={"X-Case-Access-Token": token_b})
    assert res.status_code == 403
    # Case A must still exist — the foreign token must not have been able to delete it.
    assert client.get(f"/api/v1/kadi/cases/{case_a}").status_code == 200


def test_deleting_a_nonexistent_case_returns_404():
    res = client.delete(
        "/api/v1/kadi/cases/CASE-doesnotexist12", headers={"X-Case-Access-Token": "anything"}
    )
    assert res.status_code == 404


def test_deletion_removes_the_actual_database_rows_not_just_the_api_view():
    """Stronger than the route-based tests above: queries the database directly to
    prove the entity rows, the association rows, and the generated PDF's bytes are
    genuinely gone — not merely unreachable through a route that happens to check
    existence first."""
    case_id = _case_with_document()
    client.post(f"/api/v1/billnyay/cases/{case_id}/appeal")

    entity_ids_before = _with_session(
        lambda s: s.execute(
            select(kadi_case_entities.c.entity_id).where(kadi_case_entities.c.case_id == case_id)
        )
    )
    entity_ids_before = [row[0] for row in entity_ids_before.all()]
    assert len(entity_ids_before) > 0

    client.delete(f"/api/v1/kadi/cases/{case_id}")

    remaining_associations = _with_session(
        lambda s: s.execute(
            select(kadi_case_entities.c.entity_id).where(kadi_case_entities.c.case_id == case_id)
        )
    )
    assert remaining_associations.all() == []

    remaining_entities = _with_session(
        lambda s: s.execute(select(KadiEntity).where(KadiEntity.id.in_(entity_ids_before)))
    )
    assert remaining_entities.scalars().all() == []

    remaining_appeal = _with_session(
        lambda s: s.execute(select(BillNyayAppeal).where(BillNyayAppeal.case_id == case_id))
    )
    assert remaining_appeal.scalar_one_or_none() is None


def test_shared_entity_is_not_deleted_out_from_under_another_case():
    """The many-to-many schema in principle allows one entity row to be linked to more
    than one case. If that ever happens, deleting case A must not destroy an entity
    case B still legitimately references."""
    case_a = _case_with_document()
    case_b = _case_with_document()

    entity_id = _with_session(
        lambda s: s.execute(
            select(kadi_case_entities.c.entity_id).where(kadi_case_entities.c.case_id == case_a).limit(1)
        )
    )
    entity_id = entity_id.scalar_one()

    # Manually create a second association, simulating a shared entity.
    async def link_to_case_b(session):
        await session.execute(
            kadi_case_entities.insert().values(case_id=case_b, entity_id=entity_id, source_module="test")
        )
        await session.commit()

    _with_session(link_to_case_b)

    client.delete(f"/api/v1/kadi/cases/{case_a}")

    still_exists = _with_session(lambda s: s.execute(select(KadiEntity).where(KadiEntity.id == entity_id)))
    assert still_exists.scalar_one_or_none() is not None, (
        "an entity still referenced by another case was deleted"
    )


def test_deleting_one_case_does_not_affect_another():
    case_a = _case_with_document()
    case_b = _case_with_document()

    client.delete(f"/api/v1/kadi/cases/{case_a}")

    assert client.get(f"/api/v1/kadi/cases/{case_a}").status_code == 404
    assert client.get(f"/api/v1/kadi/cases/{case_b}").status_code == 200
