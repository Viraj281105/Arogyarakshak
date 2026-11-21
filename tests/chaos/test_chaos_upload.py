"""Chaos: oversized, malformed and disk-full uploads.

Zero retention (ADR-003): a document is never written to disk by the application, so a full
disk must not stop a small upload. The one place bytes can touch disk is the multipart parser's
spill file for a large body; that failure must still give a clean JSON error.
"""

import errno
import tempfile

import pytest

from app.config import settings
from app.services import case_ingestion
from chaos_harness import K, TEXT_BILL, assert_no_leak, client, jobs, new_case, stream_events, upload
from chaos_harness import *  # noqa: F401,F403


def _no_space(*args, **kwargs):
    raise OSError(errno.ENOSPC, "No space left on device")


def test_an_oversized_upload_is_rejected_413_and_nothing_is_recorded(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 1024)
    case_id = new_case()
    res = upload(case_id, b"A" * 1025)
    assert res.status_code == 413
    body = res.json()
    assert body["detail"] == body["message"] and "limit" in body["detail"]
    assert "AAAA" not in res.text
    assert jobs(case_id) == [], "a rejected document leaves no job row"
    assert case_id not in case_ingestion.processing_status


def test_an_upload_exactly_at_the_limit_is_accepted(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", len(TEXT_BILL))
    case_id = new_case()
    assert upload(case_id).status_code == 202


def test_the_server_stays_healthy_after_oversized_uploads(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 512)
    case_id = new_case()
    for _ in range(3):
        assert upload(case_id, b"B" * 4096).status_code == 413
    assert client.get("/health/live").status_code == 200
    monkeypatch.setattr(settings, "max_upload_bytes", 10 * 1024 * 1024)
    assert upload(case_id).status_code == 202


@pytest.mark.parametrize(
    "data,name,status",
    [(b"", "empty.txt", 400), (b"x", "malware.exe", 415), (b"x", "noextension", 415)],
)
def test_malformed_uploads_get_the_documented_error_payload(data, name, status):
    case_id = new_case()
    res = upload(case_id, data, name)
    assert res.status_code == status
    body = res.json()
    assert body["detail"] == body["message"]
    assert jobs(case_id) == []


def test_a_request_without_a_file_is_a_422_with_the_documented_payload():
    case_id = new_case()
    res = client.post(f"{K}/cases/{case_id}/upload")
    assert res.status_code == 422
    assert res.json()["message"] == "Request validation failed"


def test_a_full_disk_does_not_stop_a_small_upload(monkeypatch, tmp_path):
    """Documents live in memory only. With every attempt to create a temporary file failing
    (disk full), a small upload is still accepted and processed to completion."""
    monkeypatch.setattr(tempfile, "TemporaryFile", _no_space)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", _no_space)
    monkeypatch.setattr(tempfile, "mkstemp", _no_space)
    case_id = new_case()
    assert upload(case_id).status_code == 202
    assert stream_events(case_id)[-1]["status"] == "completed"
    assert [s for s, _ in jobs(case_id)] == ["completed"]


def _spool_failure(monkeypatch):
    monkeypatch.setattr(tempfile, "TemporaryFile", _no_space)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", _no_space)
    case_id = new_case()
    return case_id, upload(case_id, b"C" * (2 * 1024 * 1024) + b"\n")


def test_a_full_disk_while_spooling_a_large_body_is_a_clean_json_error(monkeypatch):
    """Bodies over the multipart parser's in-memory spool (1 MiB) roll over to a temp file. When
    that write fails the client gets a JSON error with no path or errno text, nothing is
    recorded, and the process stays up."""
    case_id, res = _spool_failure(monkeypatch)
    assert res.status_code >= 400
    body = res.json()
    assert "detail" in body
    assert_no_leak(res.text, "No space left", "ENOSPC", "tmp")
    assert client.get("/health/live").status_code == 200
    assert jobs(case_id) == []


@pytest.mark.xfail(
    reason="DEFECT: a server-side ENOSPC while Starlette spools a large multipart body is reported as "
           "400 'There was an error parsing the body' (a client error), so alerts on 5xx never see it "
           "and clients are told to fix their request. Comes from the framework's form parser; the fix "
           "(catching OSError around the form read and answering 507/503) is not trivial and isolated.",
    strict=True,
)
def test_a_full_disk_while_spooling_is_a_server_error_not_a_client_error(monkeypatch):
    _, res = _spool_failure(monkeypatch)
    assert res.status_code >= 500


def test_no_document_bytes_are_ever_written_to_the_filesystem(monkeypatch, tmp_path):
    """Spy on write-mode open(): processing a document may write nothing that contains it."""
    import builtins

    real_open = builtins.open
    written = []

    def spy(file, mode="r", *args, **kwargs):
        if any(flag in str(mode) for flag in "wax+") and not str(file).endswith((".db", ".db-journal")):
            written.append(str(file))
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)
    case_id = new_case()
    assert upload(case_id).status_code == 202
    assert stream_events(case_id)[-1]["status"] == "completed"
    assert written == [], f"unexpected writes: {written}"
