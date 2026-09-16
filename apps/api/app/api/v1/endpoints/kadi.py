"""
Kadi API Endpoints.

Case creation, document uploads (OCR parsing), entity extraction and resolution (#31),
ABDM/FHIR record import (#54), resolution feedback and threshold calibration (#88), the
case knowledge graph (#86) and auto-triggered module insights (#32).
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
import hashlib
import os
import secrets
import time
import uuid
import logging
import json
import asyncio

from contextlib import asynccontextmanager
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File, BackgroundTasks, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.auto_triggers import readiness_for_case, run_auto_triggers
from app.background import get_background_session
from app.config import settings
from app.case_auth import generate_case_access_token, require_case_access
from app.consent import require_case_consent
from app.database import get_db
from app.latency_metrics import tracker as latency_tracker, LatencySummary, LatencySample
from app.kadi_resolution import (
    ALL_TYPES_SCOPE,
    DecisionAlreadyResolved,
    DecisionStale,
    MentionInput,
    apply_feedback,
    latest_calibration,
    recalibrate,
    resolve_and_attach,
)
from app.models import (
    BillNyayAppeal,
    DaaviSetuClaim,
    KadiCase,
    KadiCaseDocument,
    KadiEntity,
    KadiModuleInsight,
    KadiResolutionDecision,
    KadiThresholdCalibration,
    SchemeSetuCaseProfile,
    kadi_case_entities,
)
# OCR parser and extraction agent from kadi shared layer
from kadi.ocr.ocr_parser import parse_document
from kadi.extraction import extract_entities_from_text
from kadi.fhir_import import FhirBundleError, parse_fhir_bundle
from kadi.graph import CaseGraph, EntityRecord, PendingLink, StayInfo, build_case_graph
from kadi.redaction import redact_pii
from kadi.resolution import RESOLVABLE_ENTITY_TYPES, ResolutionThresholds

logger = logging.getLogger("arogyarakshak.api.kadi")
router = APIRouter()

# In-memory document processing status stream mapping.
# Single-process only: under multiple workers a stream may poll a different process.
processing_status: Dict[str, List[Dict[str, Any]]] = {}

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


# --- Pydantic Schemas ---------------------------------------------------------
class CaseCreate(BaseModel):
    consent_opt_in: bool = Field(default=False, description="Patient opt-in for cross-module context sharing")


class CaseResponse(BaseModel):
    id: str
    status: str
    consent_opt_in: bool
    total_charged: float
    created_at: Any

    model_config = ConfigDict(from_attributes=True)


class CaseCreatedResponse(CaseResponse):
    # Returned ONLY here, exactly once. Every other case-reading response uses
    # CaseResponse (no access_token field) so the secret is never echoed back on a
    # later GET — losing it means the case is permanently unrecoverable by design, the
    # same trade-off as an API key shown once at creation.
    access_token: str = Field(
        ..., description="Case access token (ADR-009). Store it — it is shown only once "
        "and is required on every subsequent request for this case."
    )


class EntityResponse(BaseModel):
    id: str
    name: str
    type: str
    value: Optional[str]
    meta: Optional[Dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)



class CaseDetailResponse(BaseModel):
    case: CaseResponse
    entities: List[EntityResponse]


class ResolutionDecisionResponse(BaseModel):
    id: str
    entity_type: str
    action: str
    status: str
    source: str
    confidence: float
    mention_name: Optional[str]
    mention_entity_id: Optional[str]
    candidate_entity_id: str
    candidate_name: str
    signals: List[Dict[str, Any]]
    reasons: List[str]
    thresholds: Dict[str, Any]
    feedback_same_entity: Optional[bool]
    created_at: Any


class ResolutionFeedbackRequest(BaseModel):
    same_entity: bool = Field(..., description="true: the two refer to the same entity; false: they do not")


class CalibrationAttempt(BaseModel):
    scope: str
    status: str
    merge_threshold: float
    ask_threshold: float
    sample_count: int
    reasons: List[str]


class ResolutionFeedbackResponse(BaseModel):
    decision: ResolutionDecisionResponse
    calibration: List[CalibrationAttempt]


class AbdmImportResponse(BaseModel):
    case_id: str
    duplicate: bool = False
    record_types: List[str] = Field(default_factory=list)
    entities_in_bundle: int = 0
    created: int = 0
    merged: int = 0
    pending_review: int = 0
    skipped: Dict[str, int] = Field(default_factory=dict)
    dropped_for_privacy: Dict[str, int] = Field(default_factory=dict)
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


def _decision_response(decision: KadiResolutionDecision) -> ResolutionDecisionResponse:
    payload = decision.mention_payload or {}
    return ResolutionDecisionResponse(
        id=decision.id,
        entity_type=decision.entity_type,
        action=decision.action,
        status=decision.status,
        source=decision.source,
        confidence=decision.confidence,
        mention_name=payload.get("name"),
        mention_entity_id=decision.mention_entity_id,
        candidate_entity_id=decision.candidate_entity_id,
        candidate_name=decision.candidate_name,
        signals=decision.signals or [],
        reasons=decision.reasons or [],
        thresholds=decision.thresholds or {},
        feedback_same_entity=decision.feedback_same_entity,
        created_at=decision.created_at,
    )


async def _load_case_with_entities(db: AsyncSession, case_id: str) -> Optional[KadiCase]:
    result = await db.execute(
        select(KadiCase)
        .options(selectinload(KadiCase.entities))
        .where(KadiCase.id == case_id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


# --- Async Helper Task --------------------------------------------------------
async def process_document_background(
    case_id: str,
    file_bytes: bytes,
    filename: str,
    db: Optional[AsyncSession] = None,
    digest: Optional[str] = None,
):
    """Processes an uploaded document: OCR, extraction, entity resolution, persistence,
    then consent-bounded module auto-triggers."""
    logger.info(f"Background task starting: OCR parsing for case={case_id}, file={filename}")
    digest = digest or hashlib.sha256(file_bytes).hexdigest()
    try:
        # Step 1: OCR parsing
        processing_status[case_id].append({"status": "ocr_start", "progress": 30, "log": "Running document OCR parser..."})
        parsed = parse_document(file_bytes=file_bytes, filename=filename)

        # A parse failure must stop the pipeline. Previously the parser substituted a
        # placeholder sentence, so the stream reported "processed successfully" and the
        # user was shown an empty audit of a document that was never actually read.
        if not parsed.get("extraction_ok", False):
            reason = parsed.get("extraction_error") or "The document could not be read."
            logger.warning("Extraction failed for case=%s file=%s: %s", case_id, filename, reason)
            processing_status[case_id].append({
                "status": "failed",
                "progress": 100,
                "log": reason,
            })
            _record_case_latency(case_id, "failed")
            return

        text = parsed.get("full_text_content", "")
        line_items = parsed.get("line_items", [])

        # Step 2: Extraction using Kadi shared extraction agent (Groq API or heuristic fallback)
        processing_status[case_id].append({"status": "extraction_start", "progress": 60, "log": "Extracting clinical & billing entities with Kadi agent..."})
        extracted = extract_entities_from_text(text, api_key=settings.groq_api_key, model=settings.groq_model)

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


# --- Route Implementations ----------------------------------------------------

@router.post("/cases", response_model=CaseCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_case(case_in: CaseCreate, db: AsyncSession = Depends(get_db)):
    """Creates a new patient case session and its one-time access token (ADR-009)."""
    # 16 hex chars (64 bits) rather than 8 (32 bits): raises the cost of blindly guessing
    # a case id, but — per ADR-008/ADR-009 — entropy alone is not authorization. The
    # access_token below is the actual authorization boundary; every subsequent
    # case-scoped request must present it.
    case_id = f"CASE-{secrets.token_hex(8)}"
    plaintext_token, token_hash = generate_case_access_token()
    case = KadiCase(
        id=case_id,
        consent_opt_in=case_in.consent_opt_in,
        status="active",
        total_charged=0.0,
        access_token_hash=token_hash,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
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
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
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
        response.status_code = status.HTTP_200_OK
        return {
            "status": "duplicate",
            "message": DUPLICATE_DOCUMENT_LOG,
            "case_id": case_id,
            "filename": file.filename,
        }

    processing_status[case_id] = [received]

    # 5. Queue processing task
    background_tasks.add_task(
        process_document_background,
        case_id=case_id,
        file_bytes=file_bytes,
        filename=file.filename,
        digest=digest,
    )

    return {
        "status": "processing",
        "message": "Document uploaded successfully and queued for OCR extraction.",
        "case_id": case_id,
        "filename": file.filename
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


@router.get("/metrics/latency/recent", response_model=List[LatencySample])
async def latency_metrics_recent(limit: int = Query(20, ge=1, le=200)):
    """Most recent individual latency samples, newest first — for spotting which
    specific uploads are driving p95/max rather than only the aggregate."""
    return latency_tracker.recent(limit=limit)


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
    the actual erasure mechanism that claim implied. See ADR-010 for what this does and
    does not cover (BimaNyay's dispute records are a separate, not-yet-linked data
    domain and are unaffected by this route).

    Deletes explicitly in Python rather than relying solely on the database's
    ON DELETE CASCADE, so behaviour is identical under SQLite (used in tests, where
    foreign-key enforcement is not enabled by default) and Postgres (production).
    KadiEntity rows are only deleted once they have no OTHER case association left —
    the many-to-many schema in principle allows an entity to be shared across cases,
    so an entity must not be destroyed out from under a different case that still
    references it.
    """
    entity_ids_result = await db.execute(
        select(kadi_case_entities.c.entity_id).where(kadi_case_entities.c.case_id == case_id)
    )
    entity_ids = [row[0] for row in entity_ids_result.all()]

    await db.execute(delete(kadi_case_entities).where(kadi_case_entities.c.case_id == case_id))

    if entity_ids:
        still_linked_result = await db.execute(
            select(kadi_case_entities.c.entity_id.distinct()).where(
                kadi_case_entities.c.entity_id.in_(entity_ids)
            )
        )
        still_linked = {row[0] for row in still_linked_result.all()}
        now_orphaned = [eid for eid in entity_ids if eid not in still_linked]
        if now_orphaned:
            await db.execute(delete(KadiEntity).where(KadiEntity.id.in_(now_orphaned)))

    await db.execute(delete(KadiCaseDocument).where(KadiCaseDocument.case_id == case_id))
    await db.execute(delete(KadiResolutionDecision).where(KadiResolutionDecision.case_id == case_id))
    await db.execute(delete(KadiModuleInsight).where(KadiModuleInsight.case_id == case_id))
    await db.execute(delete(SchemeSetuCaseProfile).where(SchemeSetuCaseProfile.case_id == case_id))
    await db.execute(delete(BillNyayAppeal).where(BillNyayAppeal.case_id == case_id))
    await db.execute(delete(DaaviSetuClaim).where(DaaviSetuClaim.case_id == case_id))
    await db.execute(delete(KadiCase).where(KadiCase.id == case_id))
    await db.commit()

    processing_status.pop(case_id, None)
    logger.info("Case %s and all derived records permanently deleted.", case_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Entity resolution: review and feedback (#31, #88) ------------------------

@router.get("/cases/{case_id}/resolutions", response_model=List[ResolutionDecisionResponse])
async def list_resolution_decisions(
    case_id: str,
    status_filter: Optional[str] = Query(
        None, alias="status", pattern="^(pending|auto_merged|confirmed|rejected|split|superseded)$"
    ),
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Entity-resolution decisions for this case. `status=pending` lists the "are these the
    same?" questions awaiting the user; `auto_merged` lists merges the user can dispute.

    Not consent-gated: like GET /cases/{case_id}, it only exposes Kadi's own context for
    the case, not another module's view of it (see app.consent). Still access-gated
    (app.case_auth) — every case-scoped route is, regardless of consent."""
    query = select(KadiResolutionDecision).where(KadiResolutionDecision.case_id == case_id)
    if status_filter:
        query = query.where(KadiResolutionDecision.status == status_filter)
    rows = (await db.execute(query.order_by(KadiResolutionDecision.created_at))).scalars().all()
    return [_decision_response(d) for d in rows]


@router.post(
    "/cases/{case_id}/resolutions/{decision_id}/feedback", response_model=ResolutionFeedbackResponse
)
async def submit_resolution_feedback(
    case_id: str,
    decision_id: str,
    body: ResolutionFeedbackRequest,
    _case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Applies the user's answer and records it as a calibration label.

    - pending + same_entity=true  -> the mention is folded into the existing entity
    - pending + same_entity=false -> both entities are kept
    - auto_merged + false         -> the merge is split back into its own entity
    """
    # apply_feedback needs entities eagerly loaded, which the plain row from
    # require_case_access does not have — re-fetched here rather than adding
    # selectinload to every route's dependency for the one caller that needs it.
    case = await _load_case_with_entities(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    decision = (
        await db.execute(
            select(KadiResolutionDecision).where(
                KadiResolutionDecision.id == decision_id, KadiResolutionDecision.case_id == case_id
            )
        )
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(status_code=404, detail="Resolution decision not found for this case")

    try:
        await apply_feedback(db, case, decision, body.same_entity)
    except DecisionAlreadyResolved:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This decision was already answered.")
    except DecisionStale:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The entities in this decision have changed since it was made. Refresh and try again.",
        )

    results = await recalibrate(db, decision.entity_type)
    await db.commit()

    # Entity context changed; refresh the consent-bounded module insights.
    await run_auto_triggers(db, case_id, trigger="resolution_feedback")
    await db.commit()

    return ResolutionFeedbackResponse(
        decision=_decision_response(decision),
        calibration=[
            CalibrationAttempt(
                scope=r.scope,
                status=r.status,
                merge_threshold=r.thresholds.merge,
                ask_threshold=r.thresholds.ask,
                sample_count=r.metrics.sample_count,
                reasons=r.reasons,
            )
            for r in results
        ],
    )


@router.get("/resolution/calibration")
async def resolution_calibration(db: AsyncSession = Depends(get_db)):
    """Active entity-resolution thresholds and recent recalibration attempts. Aggregate
    numbers only — no case data."""
    active: Dict[str, Any] = {}
    for scope in (ALL_TYPES_SCOPE, *sorted(RESOLVABLE_ENTITY_TYPES)):
        row = await latest_calibration(db, scope)
        if row is not None:
            active[scope] = {
                "merge": row.merge_threshold,
                "ask": row.ask_threshold,
                "calibration_id": row.id,
                "sample_count": row.sample_count,
                "metrics": row.metrics,
                "calibrated_at": row.created_at,
            }
    labeled = (
        await db.execute(
            select(func.count()).select_from(KadiResolutionDecision).where(
                KadiResolutionDecision.feedback_same_entity.is_not(None)
            )
        )
    ).scalar_one()
    recent = (
        await db.execute(
            select(KadiThresholdCalibration).order_by(KadiThresholdCalibration.created_at.desc()).limit(10)
        )
    ).scalars().all()
    return {
        "method": (
            "Deterministic, bounded recalibration of the merge and ask thresholds from user "
            "confirm/reject answers. Not RLHF: there is no reward model and no policy optimization."
        ),
        "defaults": ResolutionThresholds().model_dump(),
        "active": active,
        "labeled_decisions": labeled,
        "recent_attempts": [
            {
                "scope": r.scope,
                "status": r.status,
                "merge_threshold": r.merge_threshold,
                "ask_threshold": r.ask_threshold,
                "sample_count": r.sample_count,
                "reasons": r.reasons,
                "created_at": r.created_at,
            }
            for r in recent
        ],
    }


# --- Case knowledge graph (#86) -----------------------------------------------

@router.get("/cases/{case_id}/graph", response_model=CaseGraph)
async def case_graph(
    case_id: str,
    _case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Typed node-link graph of this case's entities. Every edge carries its evidence.

    Not consent-gated, for the same reason as GET /cases/{case_id}: it is Kadi's own view
    of the case, not another module's. Still access-gated (app.case_auth)."""
    case = await _load_case_with_entities(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    pending = (
        await db.execute(
            select(KadiResolutionDecision).where(
                KadiResolutionDecision.case_id == case_id,
                KadiResolutionDecision.status == "pending",
                KadiResolutionDecision.mention_entity_id.is_not(None),
            )
        )
    ).scalars().all()
    return build_case_graph(
        StayInfo(
            case_id=case_id,
            admission_date=case.date_admission.date().isoformat() if case.date_admission else None,
            discharge_date=case.date_discharge.date().isoformat() if case.date_discharge else None,
        ),
        [
            EntityRecord(id=e.id, name=e.name or "", type=e.type, value=e.value, meta=e.meta if isinstance(e.meta, dict) else {})
            for e in case.entities
        ],
        [
            PendingLink(
                decision_id=d.id,
                mention_entity_id=d.mention_entity_id,
                candidate_entity_id=d.candidate_entity_id,
                confidence=d.confidence,
            )
            for d in pending
        ],
    )


# --- Auto-triggered module insights (#32) -------------------------------------

@router.get("/cases/{case_id}/insights")
async def case_insights(
    case_id: str,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Readiness of every module check for this case, and the latest result of each check
    Kadi ran automatically. Consent-gated: these are other modules' analyses of the case."""
    case = require_case_consent(case)
    readiness = await readiness_for_case(db, case)
    rows = (
        await db.execute(select(KadiModuleInsight).where(KadiModuleInsight.case_id == case_id))
    ).scalars().all()
    return {
        "case_id": case_id,
        "readiness": [r.model_dump() for r in readiness],
        "insights": [
            {
                "module_check": r.module_check,
                "status": r.status,
                "trigger": r.trigger,
                "summary": r.summary,
                "missing_context": r.missing_context or [],
                "error_id": r.error_id,
                "updated_at": r.updated_at,
            }
            for r in rows
        ],
    }


# --- ABDM / FHIR record import (#54) ------------------------------------------

def _parse_iso_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.combine(date.fromisoformat(value), datetime.min.time())
    except ValueError:
        return None


@router.post("/cases/{case_id}/abdm/import", response_model=AbdmImportResponse)
async def import_abdm_records(
    case_id: str,
    request: Request,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Imports a FHIR R4 Bundle of ABHA-linked health records into this case's context.

    The bundle is supplied by the client; this service does not pull from the ABDM
    gateway. Consent-gated: pulled medical history is broader than an uploaded bill, so it
    only enters the shared cross-module context of a case whose patient opted in. Imported
    entities go through the same entity resolution as uploads.
    """
    require_case_consent(case)

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > settings.max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Bundle exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit.",
            )
    try:
        bundle = json.loads(bytes(body))
    except (UnicodeDecodeError, ValueError):
        raise HTTPException(status_code=422, detail={"message": "Request body is not valid JSON."})

    digest = hashlib.sha256(bytes(body)).hexdigest()
    try:
        parsed = parse_fhir_bundle(bundle, source_label=f"abdm_import:{digest[:12]}")
    except FhirBundleError as exc:
        raise HTTPException(status_code=422, detail={"message": f"Unsupported FHIR payload: {exc}."})

    if await _document_already_ingested(db, case_id, digest):
        return AbdmImportResponse(case_id=case_id, duplicate=True, warnings=["This bundle was already imported into this case."])

    case = await _load_case_with_entities(db, case_id)
    summary = await resolve_and_attach(
        db,
        case,
        [MentionInput(e.entity_type, e.name, e.value, e.meta) for e in parsed.entities],
        source="abdm_fhir",
    )

    warnings = list(parsed.warnings)
    for field, label, value in (
        ("date_admission", "admission", parsed.admission_date),
        ("date_discharge", "discharge", parsed.discharge_date),
    ):
        incoming = _parse_iso_date(value)
        if incoming is None:
            continue
        recorded = getattr(case, field)
        if recorded is None:
            setattr(case, field, incoming)
        elif recorded.date() != incoming.date():
            warnings.append(
                f"The bundle's {label} date ({value}) differs from the date already recorded for "
                f"this case ({recorded.date().isoformat()}); the recorded date was kept."
            )

    db.add(
        KadiCaseDocument(
            id=f"DOC-{uuid.uuid4().hex[:10]}", case_id=case_id, sha256=digest, extension=".json", source="abdm_fhir"
        )
    )
    await db.commit()

    await run_auto_triggers(db, case_id, trigger="abdm_import")
    await db.commit()

    return AbdmImportResponse(
        case_id=case_id,
        record_types=parsed.record_types,
        entities_in_bundle=len(parsed.entities),
        created=summary.created,
        merged=summary.merged,
        pending_review=summary.pending_review,
        skipped=parsed.skipped,
        dropped_for_privacy=parsed.dropped_for_privacy,
        admission_date=parsed.admission_date,
        discharge_date=parsed.discharge_date,
        warnings=warnings,
    )
