"""Impossible transitions in the human-review workflows (release-candidate pass).

Double clicks, repeated submissions and role confusion must never produce a second
decision, a second reader out of one person, or a change to a finished review.
"""

from tests.clinical_helpers import (
    K,
    accept,
    assign,
    client,
    finalize,
    full_statement,
    make_case,
    register,
    request_review,
    rh,
)


def _audit_count(case_id, event_type):
    from conftest import TestingSessionLocal
    import asyncio
    from sqlalchemy import func, select

    from app.models import KadiClinicalAuditEvent

    async def count():
        async with TestingSessionLocal() as s:
            return (
                await s.execute(
                    select(func.count()).select_from(KadiClinicalAuditEvent).where(
                        KadiClinicalAuditEvent.case_id == case_id, KadiClinicalAuditEvent.event_type == event_type
                    )
                )
            ).scalar_one()

    return asyncio.run(count())


def test_accepting_twice_records_one_acceptance_and_keeps_the_first_coi():
    case_id = make_case()
    rid, tok = register()
    review_id = request_review(case_id)
    assign(case_id, review_id, rid)
    assert accept(review_id, tok, "INDEPENDENT_REVIEWER").status_code == 200
    second = accept(review_id, tok, "TREATING_DOCTOR")
    assert second.status_code == 409, second.text
    view = client.get(f"{K}/clinical-reviews/{review_id}", headers=rh(tok)).json()
    assert view["coi_label"] == "Declares no relationship with the patient, hospital or insurer"
    assert _audit_count(case_id, "REVIEW_ACCEPTED") == 1


def test_a_second_reviewer_cannot_be_swapped_in_after_acceptance():
    case_id = make_case()
    rid, tok = register(name="Dr. First")
    other_id, other_tok = register(name="Dr. Second")
    review_id = request_review(case_id)
    assign(case_id, review_id, rid)
    accept(review_id, tok)
    swap = assign(case_id, review_id, other_id)
    assert swap.status_code == 409, swap.text
    assert client.get(f"{K}/clinical-reviews/{review_id}", headers=rh(other_tok)).status_code in (403, 404)


def test_finalizing_twice_does_not_create_a_second_version():
    case_id = make_case()
    ids = full_statement(case_id)
    assert finalize(ids["review_id"], ids["statement_id"], ids["token"]).status_code == 409
    review = client.get(f"{K}/cases/{case_id}/clinical-reviews/{ids['review_id']}").json()
    assert review["current_statement"]["statement_version"] == 1
    assert _audit_count(case_id, "STATEMENT_FINALIZED") == 1


def test_a_completed_review_accepts_no_new_draft():
    case_id = make_case()
    ids = full_statement(case_id)
    res = client.post(
        f"{K}/clinical-reviews/{ids['review_id']}/statements",
        json={"evidence_reviewed": [], "reviewer_statement": "Another opinion.", "limitations": "None."},
        headers=rh(ids["token"]),
    )
    # A new opinion must go through the explicit revision path, never a silent second draft.
    assert res.status_code in (409, 422), res.text


def test_the_reviewer_cannot_finalize_without_accepting():
    case_id = make_case()
    rid, tok = register()
    review_id = request_review(case_id)
    assign(case_id, review_id, rid)
    res = client.post(
        f"{K}/clinical-reviews/{review_id}/statements",
        json={"evidence_reviewed": [], "reviewer_statement": "Early opinion.", "limitations": "None."},
        headers=rh(tok),
    )
    assert res.status_code in (403, 409), "no statement before COI + acceptance"


def test_one_person_cannot_be_both_readers_of_a_medication_reading():
    case_id = make_case()
    flagged = client.get(f"{K}/cases/{case_id}").json()["entities"]
    med = next(e for e in flagged if e["type"] == "medicine")
    task = client.post(f"{K}/cases/{case_id}/transcriptions", json={"entity_id": med["id"], "field_type": "MEDICINE_NAME"}).json()
    rid, tok = register(category="PHARMACIST", name="Only Reader")
    first = client.post(f"{K}/cases/{case_id}/transcriptions/{task['task_id']}/assign",
                        json={"reviewer_id": rid, "share_with_reviewer_consent": True})
    assert first.status_code == 200, first.text
    again = client.post(f"{K}/cases/{case_id}/transcriptions/{task['task_id']}/assign",
                        json={"reviewer_id": rid, "share_with_reviewer_consent": True})
    assert again.status_code in (200, 409)
    client.post(f"{K}/transcriptions/{task['task_id']}/readings", json={"value": "Tab Dolo 650mg"}, headers=rh(tok))
    dup = client.post(f"{K}/transcriptions/{task['task_id']}/readings", json={"value": "Tab Dolo 650mg"}, headers=rh(tok))
    assert dup.status_code == 409
    tasks = {t["task_id"]: t for t in client.get(f"{K}/cases/{case_id}/transcriptions").json()}
    assert tasks[task["task_id"]]["status"] == "AWAITING_SECOND_REVIEW", "one person is never two independent readers"


def test_the_same_document_ingested_twice_adds_nothing_the_second_time():
    import asyncio

    from app.api.v1.endpoints.kadi import ingest_document_now
    from conftest import TestingSessionLocal

    case_id = make_case(doc=None)
    doc = b"Consultation: 700\nTab Pan 40 (Strip of 15): 60\nTotal: 760\n"

    async def twice():
        async with TestingSessionLocal() as s:
            first = await ingest_document_now(s, case_id, doc, "bill.txt")
        async with TestingSessionLocal() as s:
            second = await ingest_document_now(s, case_id, doc, "bill.txt")
        return first, second

    first, second = asyncio.run(twice())
    assert first["status"] == "completed" and first["duplicate"] is False
    assert second["status"] == "completed" and second["duplicate"] is True
    entities = client.get(f"{K}/cases/{case_id}").json()["entities"]
    assert sum(1 for e in entities if e["type"] == "medicine") == 1
    assert client.get(f"{K}/cases/{case_id}").json()["case"]["total_charged"] == 760.0


def test_the_test_database_enforces_foreign_keys_like_postgres():
    """Guard for the conftest PRAGMA: without it, insert-ordering bugs pass on SQLite and
    fail only on Postgres (see the DaaviSetu confirmation fix below)."""
    import asyncio

    from sqlalchemy import text

    from conftest import TestingSessionLocal

    async def pragma():
        async with TestingSessionLocal() as s:
            return (await s.execute(text("PRAGMA foreign_keys"))).scalar_one()

    assert asyncio.run(pragma()) == 1


def test_a_doctor_confirmation_request_is_stored_with_its_review():
    """Found by the Postgres smoke run: the fact rows were flushed before their review row
    and Postgres rejected the insert (500) — Scenario B could not be demonstrated."""
    case_id = make_case()
    # "previous_treatment_history" is a baseline clinical-fact item (daavisetu.readiness).
    res = client.post(
        f"/api/v1/daavisetu/cases/{case_id}/readiness/clinical-confirmations",
        json={"item_ids": ["previous_treatment_history"], "share_with_reviewer_consent": True},
    )
    assert res.status_code == 201, res.text
    assert res.json()["facts"], "the fact rows exist and point at the stored review"
