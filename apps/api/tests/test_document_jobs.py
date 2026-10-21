"""Persisted document processing state (ADR-019).

The live progress stream is in-memory; these tests prove the persisted job tells the
truth about every outcome, survives the stream being lost (a restart), and is erased
with the case.
"""

import asyncio
import json

from sqlalchemy import select

from app.models import KadiDocumentJob
from app.services import case_ingestion, document_jobs
from tests.clinical_helpers import K, client
from tests.conftest import TestingSessionLocal

TEXT_BILL = b"Hospital bill\nConsultation 500\nX-Ray 400\n"


def _jobs(case_id):
    async def run():
        async with TestingSessionLocal() as s:
            rows = await s.execute(select(KadiDocumentJob).where(KadiDocumentJob.case_id == case_id))
            return [(j.state, j.pipeline_version, j.error_id, j.finished_at) for j in rows.scalars().all()]
    return asyncio.run(run())


def _new_case():
    return client.post(f"{K}/cases", json={"consent_opt_in": True}).json()["id"]


def _stream_events(case_id):
    res = client.get(f"{K}/cases/{case_id}/stream")
    assert res.status_code == 200
    return [json.loads(line[6:]) for line in res.text.splitlines() if line.startswith("data: ")]


def test_successful_upload_records_a_completed_job_with_pipeline_version():
    case_id = _new_case()
    assert client.post(f"{K}/cases/{case_id}/upload", files={"file": ("bill.txt", TEXT_BILL)}).status_code == 202
    [(state, version, error_id, finished)] = _jobs(case_id)
    assert state == "completed"
    assert version == document_jobs.PIPELINE_VERSION
    assert error_id is None and finished is not None


def test_unreadable_document_records_a_failed_job(monkeypatch):
    monkeypatch.setattr(
        case_ingestion, "parse_document",
        lambda file_bytes, filename: {"extraction_ok": False, "extraction_error": "The document could not be read."},
    )
    case_id = _new_case()
    client.post(f"{K}/cases/{case_id}/upload", files={"file": ("x.png", b"\x89PNG-not-really")})
    assert [j[0] for j in _jobs(case_id)] == ["failed"]


def test_pipeline_crash_records_failed_with_the_logged_error_id(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("extractor exploded")

    monkeypatch.setattr(case_ingestion, "extract_entities_from_text", boom)
    case_id = _new_case()
    client.post(f"{K}/cases/{case_id}/upload", files={"file": ("bill.txt", TEXT_BILL)})
    [(state, _v, error_id, _f)] = _jobs(case_id)
    assert state == "failed"
    assert error_id and len(error_id) == 12, "the correlation id from the server log, not the exception text"


def test_duplicate_upload_records_a_duplicate_job_and_reprocesses_nothing():
    case_id = _new_case()
    client.post(f"{K}/cases/{case_id}/upload", files={"file": ("bill.txt", TEXT_BILL)})
    again = client.post(f"{K}/cases/{case_id}/upload", files={"file": ("bill.txt", TEXT_BILL)})
    assert again.status_code == 200 and again.json()["status"] == "duplicate"
    assert sorted(j[0] for j in _jobs(case_id)) == ["completed", "duplicate"]


def test_restart_marks_in_flight_jobs_interrupted_and_the_stream_says_so():
    """Simulates a crash mid-processing: a job left 'processing', and the in-memory
    stream gone (new process). The client must be told to re-upload, not shown 'idle'."""
    case_id = _new_case()

    async def leave_in_flight():
        async with TestingSessionLocal() as s:
            await document_jobs.create_job(s, case_id, "a" * 64, state=document_jobs.PROCESSING)
            await s.commit()
            return await document_jobs.mark_interrupted_jobs(s)

    case_ingestion.processing_status.pop(case_id, None)
    assert asyncio.run(leave_in_flight()) == 1
    assert [j[0] for j in _jobs(case_id)] == ["interrupted"]

    [event] = _stream_events(case_id)
    assert event["status"] == "failed"
    assert event["interrupted"] is True
    assert "upload it again" in event["log"]


def test_completed_last_job_still_streams_idle_after_restart():
    case_id = _new_case()
    client.post(f"{K}/cases/{case_id}/upload", files={"file": ("bill.txt", TEXT_BILL)})
    case_ingestion.processing_status.pop(case_id, None)  # the in-memory stream is gone
    [event] = _stream_events(case_id)
    assert event["status"] == "idle"


def test_a_terminal_state_is_never_overwritten():
    case_id = _new_case()

    async def run():
        async with TestingSessionLocal() as s:
            job_id = await document_jobs.create_job(s, case_id, "b" * 64)
            await s.commit()
        await document_jobs.set_state(job_id, document_jobs.COMPLETED)
        await document_jobs.set_state(job_id, document_jobs.FAILED, error_id="late")  # late, must be ignored
        async with TestingSessionLocal() as s:
            return (await s.get(KadiDocumentJob, job_id)).state

    assert asyncio.run(run()) == "completed"


def test_deleting_the_case_erases_its_jobs():
    case_id = _new_case()
    client.post(f"{K}/cases/{case_id}/upload", files={"file": ("bill.txt", TEXT_BILL)})
    assert _jobs(case_id)
    assert client.delete(f"{K}/cases/{case_id}").status_code == 204
    assert _jobs(case_id) == []


def test_job_rows_hold_no_file_name_or_content():
    """ADR-003: only the digest — never the name, which can identify the patient."""
    columns = set(KadiDocumentJob.__table__.columns.keys())
    assert columns == {"id", "case_id", "sha256", "state", "pipeline_version", "error_id",
                       "created_at", "updated_at", "finished_at"}
