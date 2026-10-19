"""Case lifecycle routes: create, upload, progress stream, read, timeline, delete, latency metrics."""

from typing import Any, Dict, List
import hashlib
import os
import time
import logging
import json
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File, BackgroundTasks, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.case_auth import require_case_access
from app.database import get_db
from app.latency_metrics import tracker as latency_tracker, LatencySummary, PublicLatencySample
from app.models import (
    KadiCase,
    KadiEntity,
)
from app.background import get_background_session
from app.services import document_jobs
from app.services.case_ingestion import (  # noqa: F401 — re-exported for existing importers
    DUPLICATE_DOCUMENT_LOG,
    MAX_TRACKED_STATUS_CASES,
    _document_already_ingested,
    _duplicate_event,
    _evict_stale_status_entries,
    _record_case_latency,
    _wrap_session,
    create_case_record,
    ingest_document_now,
    process_document_background,
    processing_status,
)
from app.services.case_purge import (  # noqa: F401 — re-exported for existing importers
    _purge_bimanyay_records_for_case,
    purge_case,
)
from app.api.v1.endpoints.kadi.schemas import (
    CaseCreate,
    CaseCreatedResponse,
    CaseDetailResponse,
)

logger = logging.getLogger("arogyarakshak.api.kadi")
router = APIRouter()


# Upload allow-list. The parser dispatches on extension, so anything outside this set
# would fall through to the generic placeholder path anyway.
ALLOWED_UPLOAD_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".txt",
    ".csv",
}


@router.post("/cases", response_model=CaseCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_case(case_in: CaseCreate, db: AsyncSession = Depends(get_db)):
    """Creates a new patient case session and its one-time access token (ADR-009)."""
    case, plaintext_token = await create_case_record(db, case_in.consent_opt_in)
    return CaseCreatedResponse(
        id=case.id,
        status=case.status,
        consent_opt_in=case.consent_opt_in,
        total_charged=case.total_charged,
        created_at=case.created_at,
        access_token=plaintext_token,
    )


@router.post("/cases/{case_id}/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    case_id: str,
    background_tasks: BackgroundTasks,
    response: Response,
    file: UploadFile = File(...),
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Uploads a clinical or financial document, scheduling background OCR extraction."""
    # 2. Validate the declared document type before reading anything into memory.
    filename = file.filename or ""
    extension = os.path.splitext(filename)[1].lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported document type '{extension or filename}'. Allowed: "
                + ", ".join(sorted(ALLOWED_UPLOAD_EXTENSIONS))
            ),
        )

    # 3. Read bytes, bounded. The whole document is held in RAM for transient parsing,
    #    so an unbounded read is a denial-of-service vector.
    file_bytes = await file.read(settings.max_upload_bytes + 1)
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty document uploaded")
    if len(file_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"Document exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB "
                "upload limit."
            ),
        )

    # Bound the in-memory status map so repeated uploads cannot grow it without limit.
    _evict_stale_status_entries()

    received = {
        "status": "upload_received",
        "progress": 10,
        "log": "Upload received. Queueing document extraction task...",
        "timestamp": time.time(),
    }
    digest = hashlib.sha256(file_bytes).hexdigest()

    # 4. The same document uploaded twice used to duplicate every entity and double the
    #    case total. Nothing is re-extracted.
    if await _document_already_ingested(db, case_id, digest):
        # Not recorded as a latency sample: no background task — and therefore no
        # OCR/extraction/write — ever runs on this path, so its near-zero duration would
        # dilute the metric rather than measure the pipeline #116 targets.
        processing_status[case_id] = [received, _duplicate_event()]
        await document_jobs.create_job(db, case_id, digest, state=document_jobs.DUPLICATE)
        await db.commit()
        response.status_code = status.HTTP_200_OK
        return {
            "status": "duplicate",
            "message": DUPLICATE_DOCUMENT_LOG,
            "case_id": case_id,
            "filename": file.filename,
        }

    processing_status[case_id] = [received]
    # ADR-019: a persisted record that this document was accepted, committed before the
    # 202 so a crash before or during processing is reported as interrupted, not idle.
    job_id = await document_jobs.create_job(db, case_id, digest)
    await db.commit()

    # 5. Queue processing task
    background_tasks.add_task(
        process_document_background,
        case_id=case_id,
        file_bytes=file_bytes,
        filename=file.filename,
        digest=digest,
        job_id=job_id,
    )

    return {
        "status": "processing",
        "message": "Document uploaded successfully and queued for OCR extraction.",
        "case_id": case_id,
        "filename": file.filename
    }


async def _idle_or_last_job_event(case_id: str) -> Dict[str, Any]:
    idle = {"status": "idle", "progress": 100, "log": "No document is being processed for this case."}
    async with get_background_session() as session:
        job = await document_jobs.latest_job(session, case_id)
    if job is None or job.state not in (document_jobs.INTERRUPTED, document_jobs.FAILED):
        return idle
    interrupted = job.state == document_jobs.INTERRUPTED
    return {
        "status": "failed",
        "progress": 100,
        "log": document_jobs.INTERRUPTED_LOG if interrupted else document_jobs.FAILED_LOG,
        "interrupted": interrupted,
        "job_id": job.id,
        "error_id": job.error_id,
    }


@router.get("/cases/{case_id}/stream")
async def stream_processing_status(
    case_id: str,
    request: Request,
    case: KadiCase = Depends(require_case_access),
):
    """Event stream route providing real-time document processing updates.

    Fixes 3 confirmed issues in the previous implementation:
    1. No case-existence/ownership check — `require_case_access` now enforces both (a
       nonexistent or unauthorized case is rejected before the generator ever starts,
       instead of holding a connection open forever polling an empty list).
    2. `settings.sse_timeout_seconds` was defined and unit-tested for its VALUE, but never
       actually read by this generator — the loop was unconditional `while True`. It is
       now enforced: the stream emits a `timeout` event and closes after that many seconds.
    3. No disconnect check — a client that closed its connection kept the generator (and
       its `asyncio.sleep` polling loop) alive server-side indefinitely. `request.is_disconnected()`
       is now checked every iteration.
    """
    async def event_generator():
        last_index = 0
        started_at = time.time()
        # Nothing has been queued for this case in this process (the upload route records
        # `upload_received` BEFORE it returns 202, so a client that connects after an
        # upload always finds it). Say so at once instead of holding the connection open
        # until the timeout: a screen opened on an already-processed case is not
        # "processing". Single-process in-memory status — see docs (known limitation).
        if case_id not in processing_status:
            # ADR-019: the in-memory stream does not survive a restart; the persisted job
            # does. An interrupted or failed last upload is reported, never shown as idle.
            event = await _idle_or_last_job_event(case_id)
            yield f"data: {json.dumps(event)}\n\n"
            return
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected for case %s; stopping stream.", case_id)
                return

            elapsed = time.time() - started_at
            if elapsed > settings.sse_timeout_seconds:
                yield f"data: {json.dumps({'status': 'timeout', 'progress': 100, 'log': 'Stream timed out waiting for processing to complete.'})}\n\n"
                return

            status_list = processing_status.get(case_id, [])
            if last_index < len(status_list):
                for item in status_list[last_index:]:
                    yield f"data: {json.dumps(item)}\n\n"
                last_index = len(status_list)
                if status_list and status_list[-1].get("status") in ["completed", "failed"]:
                    return
            await asyncio.sleep(0.3)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/metrics/latency", response_model=LatencySummary)
async def latency_metrics_summary():
    """End-to-end processing time monitoring (#116): p50/p95/max/mean over the most
    recent uploads that actually ran the OCR -> extraction -> entity-resolution ->
    database-write pipeline, checked against the project's 10-second target.

    In-memory, single-process, bounded — see app/latency_metrics.py. No case data is
    exposed here, only durations and outcomes, so this route carries no consent
    requirement (compare app/consent.py's per-route rule).
    """
    return latency_tracker.summary()


@router.get("/metrics/latency/recent", response_model=List[PublicLatencySample])
async def latency_metrics_recent(limit: int = Query(20, ge=1, le=200)):
    """Most recent individual latency samples, newest first — for spotting which
    specific uploads are driving p95/max rather than only the aggregate.

    SEC-06: this route is public and unauthenticated (see latency_metrics_summary's
    docstring), so samples carry only a one-way fingerprint of each case id, never the
    real id — a real case id is itself sensitive (ADR-008/ADR-009)."""
    return latency_tracker.recent(limit=limit)


@router.get("/cases/{case_id}/timeline")
async def get_case_timeline(
    case_id: str,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """What has happened to this case, in plain language, from persisted records only
    (kadi.timeline): each step carries the timestamp of the record that proves it, so a
    step is never shown before it happened. `in_progress` / `failure` come from the live
    processing status; `now` is the current medicine trust state."""
    from app.case_timeline import case_timeline

    events = processing_status.get(case_id) or []
    return await case_timeline(db, case_id, events[-1] if events else None)


@router.get("/cases/{case_id}", response_model=CaseDetailResponse)
async def get_case(
    case_id: str,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves case details and all associated extracted entities."""
    # Load entities
    entities_result = await db.execute(
        select(KadiEntity).join(KadiCase.entities).where(KadiCase.id == case_id)
    )
    entities = entities_result.scalars().all()

    return {
        "case": case,
        "entities": entities
    }


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Permanently deletes this case and everything derived from it (P1-10).

    ADR-003 has always called a case's database records "transient" / linked to a
    "temporary case UUID", but until this route existed nothing actually made that
    true — a case, its extracted entities, its redacted document excerpt, and any
    generated PDFs (the BillNyay appeal, the DaaviSetu pre-auth form) persisted
    indefinitely with no way for the patient who created it to remove them. This is
    the actual erasure mechanism that claim implied. SEC-04: BimaNyay dispute/grievance
    records that were explicitly linked to this case (case_id set — see
    app.api.v1.endpoints.bimanyay._authorize_optional_case) are now included in this
    cascade too; a BimaNyay record created without a case_id (its stand-alone mode)
    has nothing to cascade from and is unaffected, same as before.

    Deletes explicitly in Python rather than relying solely on the database's
    ON DELETE CASCADE, so behaviour is identical under SQLite (used in tests, where
    foreign-key enforcement is not enabled by default) and Postgres (production).
    KadiEntity rows are only deleted once they have no OTHER case association left —
    the many-to-many schema in principle allows an entity to be shared across cases,
    so an entity must not be destroyed out from under a different case that still
    references it.
    """
    await purge_case(db, case_id)
    await db.commit()

    processing_status.pop(case_id, None)
    logger.info("Case %s and all derived records permanently deleted.", case_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
