"""Chaos: oversized, malformed and disk-full uploads.

Zero retention (ADR-003): a document is never written to disk by the application, so a full
disk must not stop a small upload. The one place bytes can touch disk is the multipart parser's
spill file for a large body; that failure must still give a clean JSON error.
"""

import errno
import os
import tempfile

import pytest

from app.config import settings
from app.services import case_ingestion
from chaos_harness import K, TEST_DB_FILE, TEXT_BILL, assert_no_leak, client, jobs, new_case, stream_events, upload
from chaos_harness import *  # noqa: F401,F403


SPOOL_ATTEMPTS = []


def _no_space(*args, **kwargs):
    SPOOL_ATTEMPTS.append(1)
    raise OSError(errno.ENOSPC, "No space left on device")


MARKER = b"DOC-BYTES-MARKER-7f3a9c"


def _pdf():
    return b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n% " + MARKER + b"\ntrailer<</Root 1 0 R>>\n%%EOF\n"


def _png():
    import struct
    import zlib

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"tEXt", b"Comment\x00" + MARKER)
            + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00")) + chunk(b"IEND", b""))


DOCUMENTS = {
    "txt": (TEXT_BILL + b"Note " + MARKER + b"\n", "bill.txt"),
    "pdf": (_pdf(), "bill.pdf"),
    "png": (_png(), "bill.png"),
}


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


@pytest.mark.parametrize("kind", list(DOCUMENTS))
def test_a_full_disk_does_not_stop_a_small_upload(monkeypatch, kind):
    """Documents live in memory only. With every attempt to create a temporary file failing
    (disk full), a small upload of any supported type is still accepted and its job reaches a
    terminal state (a text bill completes; a synthetic PDF/PNG may fail to parse, but never because
    of the disk)."""
    SPOOL_ATTEMPTS.clear()
    monkeypatch.setattr(tempfile, "TemporaryFile", _no_space)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", _no_space)
    monkeypatch.setattr(tempfile, "mkstemp", _no_space)
    data, name = DOCUMENTS[kind]
    case_id = new_case()
    res = upload(case_id, data, name)
    assert res.status_code == 202, res.text
    states = [s for s, _ in jobs(case_id)]
    assert states and states[0] in {"completed", "failed"}
    assert SPOOL_ATTEMPTS == [], "a small upload must not even try to create a temporary file"
    if kind == "txt":
        assert states == ["completed"] and stream_events(case_id)[-1]["status"] == "completed"


def _spool_failure(monkeypatch):
    SPOOL_ATTEMPTS.clear()
    monkeypatch.setattr(tempfile, "TemporaryFile", _no_space)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", _no_space)
    case_id = new_case()
    return case_id, upload(case_id, b"C" * (2 * 1024 * 1024) + b"\n")


def test_a_full_disk_while_spooling_a_large_body_is_a_clean_json_error(monkeypatch):
    """Bodies over the multipart parser's in-memory spool (1 MiB) roll over to a temp file. When
    that write fails the client gets a JSON error with no path or errno text, nothing is
    recorded, and the process stays up."""
    case_id, res = _spool_failure(monkeypatch)
    assert SPOOL_ATTEMPTS, "the disk-full fault was really injected"
    assert res.status_code >= 400
    body = res.json()
    assert "detail" in body
    assert_no_leak(res.text, "No space left", "ENOSPC", "tmp")
    assert client.get("/health/live").status_code == 200
    assert jobs(case_id) == []


def test_a_full_disk_while_spooling_is_a_server_error_not_a_client_error(monkeypatch):
    _, res = _spool_failure(monkeypatch)
    assert res.status_code >= 500


# Not application output: the test database files, and the cache directory the torch library
# (a dependency of the OCR engine) creates in the temp directory the first time it is imported.
# Document bytes inside either would still fail the marker scan below.
_IGNORED_PREFIXES = ("test_temp", TEST_DB_FILE, "torchinductor_")


def _entries(path):
    return sorted(n for n in os.listdir(path) if not n.startswith(_IGNORED_PREFIXES))


def _files_containing(root, marker):
    hits = []
    for folder, _dirs, names in os.walk(root):
        for name in names:
            full = os.path.join(folder, name)
            try:
                with open(full, "rb") as handle:
                    if marker in handle.read():
                        hits.append(full)
            except OSError:
                pass
    return hits


@pytest.mark.parametrize("kind", list(DOCUMENTS))
def test_no_document_bytes_are_ever_written_to_the_filesystem(monkeypatch, kind):
    """Zero retention, demonstrated at every layer a write could go through: write-mode
    ``open`` (builtins and io), ``os.open`` with write flags (which is what ``tempfile`` uses),
    ``os.write`` of the document marker, and the temp directory and working directory listings
    before and after. The temp directory is a private one so other processes cannot disturb the
    snapshot."""
    import builtins
    import io

    private_tmp = tempfile.mkdtemp(prefix="chaos-tmp-")
    monkeypatch.setattr(tempfile, "tempdir", private_tmp)
    before = (_entries(private_tmp), _entries(os.getcwd()), tempfile.gettempdir())

    writes = []
    real_open, real_io_open, real_os_open, real_write = builtins.open, io.open, os.open, os.write
    write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC

    def spy_open(real):
        def inner(file, mode="r", *args, **kwargs):
            if any(flag in str(mode) for flag in "wax+") and not os.path.basename(str(file)).startswith(TEST_DB_FILE):
                writes.append(f"open({file!r}, {mode!r})")
            return real(file, mode, *args, **kwargs)

        return inner

    def spy_os_open(path, flags, *args, **kwargs):
        if flags & write_flags and not os.path.basename(str(path)).startswith(TEST_DB_FILE):
            writes.append(f"os.open({path!r}, {flags})")
        return real_os_open(path, flags, *args, **kwargs)

    def spy_os_write(fd, data):
        if MARKER in bytes(data):
            writes.append(f"os.write(fd={fd}) carried the document")
        return real_write(fd, data)

    monkeypatch.setattr(builtins, "open", spy_open(real_open))
    monkeypatch.setattr(io, "open", spy_open(real_io_open))
    monkeypatch.setattr(os, "open", spy_os_open)
    monkeypatch.setattr(os, "write", spy_os_write)

    data, name = DOCUMENTS[kind]
    case_id = new_case()
    res = upload(case_id, data, name)
    assert res.status_code == 202, res.text
    jobs(case_id)
    stream_events(case_id)

    after = (_entries(private_tmp), _entries(os.getcwd()), tempfile.gettempdir())
    assert writes == [], f"unexpected filesystem writes: {writes}"
    assert after == before, f"files appeared or disappeared: {before} -> {after}"
    assert _files_containing(private_tmp, MARKER) == [], "document bytes found in the temp directory"
    os.rmdir(private_tmp)
