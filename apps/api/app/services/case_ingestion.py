"""
Kadi case creation and document ingestion — application use case.

Moved out of ``app.api.v1.endpoints.kadi`` (ADR-018). The upload route queues
``process_document_background``; the demo scenario loader awaits ``ingest_document_now``.
The uploaded bytes live only in this call's memory (ADR-003): they are never written to
disk or the database, so an interrupted run cannot be retried from storage — see
ADR-019 and ``app.services.document_jobs`` for how that state is made visible instead.

``processing_status`` is the in-process SSE event log. It is single-process by design;
running more than one API worker or replica breaks live progress streaming (ADR-019).
"""

import hashlib
import logging
import os
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from dawacheck.price_basis import annotate_medicine_price_facts
from fastapi.concurrency import run_in_threadpool
from kadi.clinical_review.transcription import OcrSegment, select_uncertain_segments
from kadi.extraction import extract_entities_from_text
from kadi.line_items import ground_medicine_source_lines
from kadi.ocr.ocr_parser import parse_document
from kadi.redaction import redact_pii
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auto_triggers import run_auto_triggers
from app.background import get_background_session
from app.case_auth import generate_case_access_token
from app.clinical.context import scan_document_for_safety
from app.clinical.demo_ocr import REPLAY_LOG as DEMO_REPLAY_LOG
from app.clinical.demo_ocr import demo_ocr_replay
from app.clinical.transcription_service import create_tasks_from_ocr
from app.config import settings
from app.kadi_resolution import (
    MentionInput,
    resolve_and_attach,
)
from app.latency_metrics import tracker as latency_tracker
from app.models import (
    KadiCase,
    KadiCaseDocument,
)
from app.services import document_jobs

logger = logging.getLogger("arogyarakshak.api.kadi")


# In-memory document processing status stream mapping.
# Single-process only: under multiple workers a stream may poll a different process.
processing_status: Dict[str, List[Dict[str, Any]]] = {}


# Cap on tracked cases before the oldest entries are dropped.
MAX_TRACKED_STATUS_CASES = 500

DUPLICATE_DOCUMENT_LOG = (
    "This document was already processed for this case. No entities were added and the "
    "case total is unchanged."
)


def _evict_stale_status_entries() -> None:
    """Bounds the in-memory status map.

    It previously grew for the lifetime of the process, one entry per upload, with nothing
    ever removed. Completed and failed streams are dropped first, then the oldest entries.
    """
    if len(processing_status) < MAX_TRACKED_STATUS_CASES:
        return

    finished = [
        key
        for key, events in processing_status.items()
        if events and events[-1].get("status") in ("completed", "failed", "timeout")
    ]
    for key in finished:
        processing_status.pop(key, None)

    while len(processing_status) >= MAX_TRACKED_STATUS_CASES:
        processing_status.pop(next(iter(processing_status)), None)


@asynccontextmanager
async def _wrap_session(session: AsyncSession):
    yield session


async def _document_already_ingested(session: AsyncSession, case_id: str, digest: str) -> bool:
    result = await session.execute(
        select(KadiCaseDocument.id).where(KadiCaseDocument.case_id == case_id, KadiCaseDocument.sha256 == digest)
    )
    return result.first() is not None


def _duplicate_event() -> Dict[str, Any]:
    return {
        "status": "completed",
        "progress": 100,
        "log": DUPLICATE_DOCUMENT_LOG,
        "duplicate_document": True,
        "timestamp": time.time(),
    }


def _record_case_latency(case_id: str, outcome: str) -> None:
    """Records end-to-end processing time (#116): upload_received -> terminal event.

    Looks up the start timestamp from the case's own event stream rather than threading
    an extra parameter through every call site — `processing_status[case_id][0]` is
    always the `upload_received` event, set once at upload before any background task
    is queued. Silently no-ops if the stream is missing or malformed (e.g. evicted by
    `_evict_stale_status_entries` under extreme load) rather than raising — a metrics
    hook must never be able to fail the request it is measuring.
    """
    events = processing_status.get(case_id)
    if not events:
        return
    start_ts = events[0].get("timestamp")
    if start_ts is None:
        return
    duration = time.time() - start_ts
    if duration < 0:
        return
    latency_tracker.record(case_id, duration, outcome)


async def process_document_background(
    case_id: str,
    file_bytes: bytes,
    filename: str,
    db: Optional[AsyncSession] = None,
    digest: Optional[str] = None,
    job_id: Optional[str] = None,
):
    """Processes an uploaded document: OCR, extraction, entity resolution, persistence,
    then consent-bounded module auto-triggers.

    ``job_id`` (ADR-019) is the persisted ``kadi_document_jobs`` row the upload created.
    Its terminal state mirrors the last event of this run's progress stream.
    """
    # Same list object the pipeline appends to, even if a later upload replaces the map entry.
    events = processing_status.setdefault(case_id, [])
    await document_jobs.set_state(job_id, document_jobs.PROCESSING)
    # A cancellation (shutdown) propagates and leaves the job in flight on purpose: the
    # next start-up marks it interrupted.
    await _run_pipeline(case_id, file_bytes, filename, db=db, digest=digest)
    terminal = events[-1] if events else {}
    if terminal.get("status") == "completed":
        state = document_jobs.DUPLICATE if terminal.get("duplicate_document") else document_jobs.COMPLETED
    else:
        state = document_jobs.FAILED
    await document_jobs.set_state(job_id, state, terminal.get("error_id"))


async def _run_pipeline(
    case_id: str,
    file_bytes: bytes,
    filename: str,
    db: Optional[AsyncSession] = None,
    digest: Optional[str] = None,
):
    # The file name can identify the patient (see KadiCaseDocument); log the type only.
    extension = os.path.splitext(filename or "")[1].lower() or "(none)"
    logger.info("Background task starting: OCR parsing for case=%s, type=%s", case_id, extension)
    digest = digest or hashlib.sha256(file_bytes).hexdigest()
    try:
        # Step 1: OCR parsing.
        # SEC-01: parse_document is synchronous, CPU-heavy work (PyMuPDF page parsing,
        # EasyOCR inference) — calling it directly here would block the single event
        # loop for the entire OCR duration, stalling every other request (including
        # /health and every other case's SSE stream) for as long as this document takes
        # to read. run_in_threadpool runs it on FastAPI's worker thread pool instead.
        processing_status[case_id].append({"status": "ocr_start", "progress": 30, "log": "Running document OCR parser..."})
        # Demo mode only: the committed synthetic Scenario C document replays a recorded
        # OCR + extraction result (app.clinical.demo_ocr) so the demo is reproducible.
        replay = demo_ocr_replay(digest, settings.clinical_demo_mode)
        if replay is not None:
            parsed, replayed_extraction = replay
            processing_status[case_id].append({"status": "demo_fixture", "progress": 35, "log": DEMO_REPLAY_LOG})
        else:
            replayed_extraction = None
            parsed = await run_in_threadpool(parse_document, file_bytes=file_bytes, filename=filename)

        # A parse failure must stop the pipeline. Previously the parser substituted a
        # placeholder sentence, so the stream reported "processed successfully" and the
        # user was shown an empty audit of a document that was never actually read.
        if not parsed.get("extraction_ok", False):
            reason = parsed.get("extraction_error") or "The document could not be read."
            logger.warning("Extraction failed for case=%s type=%s: %s", case_id, extension, reason)
            processing_status[case_id].append({
                "status": "failed",
                "progress": 100,
                "log": reason,
            })
            _record_case_latency(case_id, "failed")
            return

        text = parsed.get("full_text_content", "")
        line_items = parsed.get("line_items", [])

        # Step 2: Extraction using Kadi shared extraction agent (Groq API or heuristic
        # fallback). SEC-01: extract_entities_from_text makes a synchronous
        # urllib.request.urlopen call (kadi/extraction.py) when GROQ_API_KEY is
        # configured — a blocking network call directly on the event loop, same
        # starvation risk as the OCR step above.
        processing_status[case_id].append({"status": "extraction_start", "progress": 60, "log": "Extracting clinical & billing entities with Kadi agent..."})
        if replayed_extraction is not None:
            extracted = replayed_extraction
        else:
            extracted = await run_in_threadpool(
                extract_entities_from_text, text, api_key=settings.groq_api_key, model=settings.groq_model
            )

        # Step 3: Entity resolution and database write using dedicated session
        processing_status[case_id].append({"status": "database_write", "progress": 80, "log": "Saving structured entities to database..."})

        if db is not None and getattr(db, "is_active", False):
            session_cm = _wrap_session(db)
        else:
            session_cm = get_background_session()

        async with session_cm as session:
            result = await session.execute(
                select(KadiCase).options(selectinload(KadiCase.entities)).where(KadiCase.id == case_id)
            )
            case = result.scalar_one_or_none()
            if not case:
                logger.error(f"Case {case_id} not found during background processing.")
                processing_status[case_id].append({"status": "failed", "progress": 100, "log": "Failed: Case not found"})
                _record_case_latency(case_id, "failed")
                return

            # Re-checked here as well as at upload: two identical uploads can be queued
            # before either finishes.
            if await _document_already_ingested(session, case_id, digest):
                processing_status[case_id].append(_duplicate_event())
                _record_case_latency(case_id, "completed")
                return

            mentions: List[MentionInput] = []
            total_cost = 0.0

            # 1. Billing line items from OCR. Never merged by entity resolution: two
            # identical bill lines are separate charges (possible double billing).
            for item in line_items:
                mentions.append(
                    MentionInput(
                        entity_type="billing_item",
                        name=item["item"],
                        value=str(item["charged"]),
                        meta={"charged": item["charged"], "source_file": filename},
                    )
                )
                total_cost += item["charged"]

            # 2. Structured clinical entities from extraction agent
            extraction_meta = {"source_file": filename, "source": "kadi_extraction"}
            if extracted.hospital_name:
                mentions.append(
                    MentionInput("hospital", extracted.hospital_name, extracted.hospital_name, dict(extraction_meta))
                )

            # The patient's name is deliberately NOT persisted. It is a direct identifier,
            # ADR-003 limits stored records to de-identified clinical metadata, and no
            # module reads it: DaaviSetu takes patient_name from its own request payload.
            # It stays available in-memory to the extraction result for this request only.

            if extracted.diagnosis:
                mentions.append(
                    MentionInput("diagnosis", extracted.diagnosis, extracted.diagnosis, dict(extraction_meta))
                )

            # Entity resolution (app.kadi_resolution) blocks by type: a procedure is only
            # ever compared with procedures. The old exact-name check compared against
            # every queued entity, so OCR's same-named billing_item line silently
            # suppressed the procedure entity BillNyay's ICD audit (#64) needs.
            for proc in extracted.procedures:
                proc_name = proc.get("name")
                if proc_name:
                    mentions.append(
                        MentionInput("procedure", proc_name, str(proc.get("amount", 0.0)), {**proc, **extraction_meta})
                    )

            # What the document says about each medicine's quantity or pack ("strip of 15",
            # "Qty 10", a "Rate per tablet" column) is read now, while the text is still in
            # memory, so DawaCheck can later compare like with like — or refuse to. Only the
            # derived facts and a short matched snippet are stored, never the line itself.
            ground_medicine_source_lines(text, extracted.medicines)
            annotate_medicine_price_facts(extracted.medicines, text)
            for med in extracted.medicines:
                med_name = med.get("name")
                if med_name:
                    mentions.append(
                        MentionInput("medicine", med_name, str(med.get("cost", 0.0)), {**med, **extraction_meta})
                    )

            # Document excerpt, with direct identifiers stripped. BillNyay's appeal
            # pipeline reads this to recover denial codes, insurer reasons and policy
            # clauses, so it cannot be dropped — but it must not retain the patient's
            # name, contact details or government IDs.
            excerpt_meta: Dict[str, Any] = {"source_file": filename, "redacted": True}
            # P0-4: an LLM-returned extraction is never trusted merely for being valid
            # JSON — surface any integrity warnings (possible prompt-injection phrasing,
            # or an LLM total_amount that could not be reconciled against a deterministic
            # reading of the same text) on the persisted record rather than dropping them.
            if extracted.extraction_warnings:
                excerpt_meta["extraction_warnings"] = extracted.extraction_warnings
            mentions.append(
                MentionInput(
                    "document_text",
                    "Document Text Excerpt",
                    redact_pii(text)[:1000],
                    excerpt_meta,
                )
            )

            summary = await resolve_and_attach(session, case, mentions, source="upload")
            processing_status[case_id].append({
                "status": "entity_resolution",
                "progress": 85,
                "log": (
                    f"Entity resolution: {summary.created} new, {summary.merged} merged into existing "
                    f"entities, {summary.pending_review} awaiting your review."
                ),
            })

            # ADR-011: OCR readings the engine itself was unsure of become human
            # transcription tasks rather than silently trusted facts. Only redacted text
            # and a location hint are kept — never the image.
            segments = [
                OcrSegment(s.get("text", ""), float(s.get("confidence", 1.0)), s.get("bbox"))
                for s in parsed.get("ocr_segments", [])
            ]
            uncertain = select_uncertain_segments(segments, threshold=settings.ocr_low_confidence_threshold)
            # Readings that cannot be linked to exactly one medicine are not dropped: the
            # medicines they may concern are held back from benchmarking (ocr_uncertainty).
            transcription_tasks = await create_tasks_from_ocr(
                session,
                case_id,
                uncertain,
                [e for e in case.entities if e.type == "medicine"],
                document_medicine_ids=[e.id for e in summary.touched() if e.type == "medicine"],
                confident_texts=[s.text for s in segments if s.confidence >= settings.ocr_low_confidence_threshold],
            )
            # ADR-011: check the WHOLE document against active safety rules while it is
            # still in memory; only rule ids and matched terms are persisted.
            await scan_document_for_safety(session, case_id, text)
            held_back = sum(
                1 for e in case.entities
                if e.type == "medicine" and isinstance(e.meta, dict)
                and (e.meta.get("ocr_uncertainty") or {}).get("status") == "UNRESOLVED"
            )
            if transcription_tasks or held_back:
                parts = []
                if transcription_tasks:
                    parts.append(
                        f"{len(transcription_tasks)} unclear handwriting/print reading(s) need a human reader "
                        "before they are trusted."
                    )
                if held_back:
                    parts.append(
                        f"{held_back} medicine(s) could not be matched to an unclear reading with certainty "
                        "and will not be price-checked until a human reads the entry."
                    )
                processing_status[case_id].append({
                    "status": "transcription_flags",
                    "progress": 87,
                    "log": " ".join(parts),
                })

            if total_cost > 0:
                case.total_charged += total_cost
            elif extracted.total_amount and extracted.total_amount > 0:
                case.total_charged += extracted.total_amount

            # Only the digest is kept (duplicate-upload guard), never the document.
            session.add(
                KadiCaseDocument(
                    id=f"DOC-{uuid.uuid4().hex[:10]}",
                    case_id=case_id,
                    sha256=digest,
                    extension=os.path.splitext(filename or "")[1].lower() or None,
                    source="upload",
                )
            )
            session.add(case)
            await session.commit()

            processing_status[case_id].append({
                "status": "module_checks",
                "progress": 90,
                "log": "Checking which modules have enough context to run automatically...",
            })
            insights = await run_auto_triggers(session, case_id, trigger="document_processed")
            await session.commit()

        completion = "Document processed successfully. Entities extracted."
        if insights:
            completion += f" {len(insights)} module check(s) ran automatically."
        if extracted.extraction_warnings:
            completion += " Note: this extraction was flagged for review — see case details."
        processing_status[case_id].append({"status": "completed", "progress": 100, "log": completion})
        _record_case_latency(case_id, "completed")
        logger.info(
            "Background task succeeded for case=%s: %d new entities, %d merged, %d pending review.",
            case_id, summary.created, summary.merged, summary.pending_review,
        )
    except Exception as e:
        # The SSE log line is rendered in the browser, so it must not carry the raw
        # exception text. The detail goes to the server log against a correlation id.
        error_id = uuid.uuid4().hex[:12]
        logger.error(
            "Background task failed [%s] for case=%s: %s", error_id, case_id, e, exc_info=True
        )
        processing_status.setdefault(case_id, []).append({
            "status": "failed",
            "progress": 100,
            "log": "Document processing failed. Please try uploading the document again.",
            "error_id": error_id,
        })
        _record_case_latency(case_id, "failed")


async def create_case_record(db: AsyncSession, consent_opt_in: bool) -> "tuple[KadiCase, str]":
    """Creates a case and its one-time access token (ADR-009); commits. Shared by the
    route below and the demo scenario loader (app.clinical.demo_control)."""
    # 16 hex chars (64 bits) rather than 8 (32 bits): raises the cost of blindly guessing
    # a case id, but — per ADR-008/ADR-009 — entropy alone is not authorization. The
    # access_token below is the actual authorization boundary; every subsequent
    # case-scoped request must present it.
    case_id = f"CASE-{secrets.token_hex(8)}"
    plaintext_token, token_hash = generate_case_access_token()
    case = KadiCase(
        id=case_id,
        consent_opt_in=consent_opt_in,
        status="active",
        total_charged=0.0,
        access_token_hash=token_hash,
        # SEC-03: server-side retention deadline, independent of the client ever coming
        # back with its token — see app.case_retention.
        expires_at=datetime.utcnow() + timedelta(days=settings.case_ttl_days),
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return case, plaintext_token


async def ingest_document_now(db: AsyncSession, case_id: str, file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Runs one document through the same pipeline an upload queues, but awaits it, and
    returns the final processing event. Used by the demo scenario loader, which must hand
    the judge a case that has finished processing."""
    digest = hashlib.sha256(file_bytes).hexdigest()
    received = {
        "status": "upload_received",
        "progress": 10,
        "log": "Upload received. Queueing document extraction task...",
        "timestamp": time.time(),
    }
    if await _document_already_ingested(db, case_id, digest):
        processing_status[case_id] = [received, _duplicate_event()]
        await document_jobs.create_job(db, case_id, digest, state=document_jobs.DUPLICATE)
        await db.commit()
    else:
        processing_status[case_id] = [received]
        job_id = await document_jobs.create_job(db, case_id, digest)
        await db.commit()
        await process_document_background(
            case_id=case_id, file_bytes=file_bytes, filename=filename, db=db, digest=digest, job_id=job_id
        )
    final = dict(processing_status.get(case_id, [{}])[-1])
    return {
        "filename": filename,
        "status": final.get("status"),
        "duplicate": bool(final.get("duplicate_document")),
        "log": final.get("log"),
    }
