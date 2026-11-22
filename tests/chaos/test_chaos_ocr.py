"""Chaos: the OCR / parsing stage crashes or reports failure.

A failed job must be recorded as failed (with the correlation id), the stream must end with a
generic message, and neither the exception text nor the document content may reach the client.
"""

import pytest

from app.services import case_ingestion
from chaos_harness import SECRET_DOCUMENT, assert_no_leak, client, jobs, new_case, stream_events, upload, K
from chaos_harness import *  # noqa: F401,F403

CRASHES = [
    RuntimeError(f"OCR engine crashed while reading {SECRET_DOCUMENT}"),
    MemoryError(f"out of memory on page text {SECRET_DOCUMENT}"),
    ValueError(f"bad pixel data {SECRET_DOCUMENT}"),
    OSError(28, f"No space left on device: /tmp/{SECRET_DOCUMENT}"),
]


@pytest.mark.parametrize("crash", CRASHES, ids=lambda e: type(e).__name__)
def test_an_ocr_crash_is_recorded_as_a_failed_job_and_does_not_leak(monkeypatch, crash):
    def boom(*args, **kwargs):
        raise crash

    monkeypatch.setattr(case_ingestion, "parse_document", boom)
    case_id = new_case()
    res = upload(case_id, b"%PDF-1.4 not really", "scan.pdf")
    assert res.status_code == 202, "the upload is accepted; failure is reported through the job"
    assert_no_leak(res.text)

    [(state, error_id)] = jobs(case_id)
    assert state == "failed" and error_id and len(error_id) == 12

    events = stream_events(case_id)
    assert events[-1]["status"] == "failed" and events[-1]["error_id"] == error_id
    assert events[-1]["log"] == "Document processing failed. Please try uploading the document again."
    assert_no_leak(str(events))


def test_an_unreadable_document_is_failed_not_reported_as_processed(monkeypatch):
    monkeypatch.setattr(
        case_ingestion, "parse_document",
        lambda file_bytes, filename: {"extraction_ok": False, "extraction_error": "The document could not be read."},
    )
    case_id = new_case()
    upload(case_id, b"\x89PNG\r\n", "photo.png")
    assert [s for s, _ in jobs(case_id)] == ["failed"]
    assert stream_events(case_id)[-1]["status"] == "failed"


def test_a_failed_document_does_not_poison_the_case(monkeypatch):
    """After a crash the same case accepts a corrected upload and completes it."""
    real = case_ingestion.parse_document
    monkeypatch.setattr(case_ingestion, "parse_document", lambda **kw: (_ for _ in ()).throw(RuntimeError("x")))
    case_id = new_case()
    upload(case_id, b"junk", "a.pdf")
    monkeypatch.setattr(case_ingestion, "parse_document", real)
    upload(case_id)
    assert sorted(s for s, _ in jobs(case_id)) == ["completed", "failed"]
    assert stream_events(case_id)[-1]["status"] == "completed"


def test_the_crash_does_not_take_the_process_down(monkeypatch):
    monkeypatch.setattr(case_ingestion, "parse_document", lambda **kw: (_ for _ in ()).throw(RuntimeError("x")))
    case_id = new_case()
    upload(case_id, b"junk", "a.pdf")
    assert client.get("/health/live").status_code == 200
    assert client.get(f"{K}/cases/{case_id}").status_code == 200


def test_a_failed_job_survives_a_lost_stream_and_is_not_shown_as_idle(monkeypatch):
    monkeypatch.setattr(case_ingestion, "parse_document", lambda **kw: (_ for _ in ()).throw(RuntimeError("x")))
    case_id = new_case()
    upload(case_id, b"junk", "a.pdf")
    case_ingestion.processing_status.pop(case_id, None)  # what a restart does
    event = stream_events(case_id)[-1]
    assert event["status"] == "failed" and "upload" in event["log"].lower()
    assert_no_leak(str(event))
