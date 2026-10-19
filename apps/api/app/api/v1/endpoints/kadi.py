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
import time
import uuid
import logging
import json
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File, BackgroundTasks, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.auto_triggers import readiness_for_case, run_auto_triggers
from app.config import settings
from app.case_auth import require_case_access
from app.consent import require_case_consent
from app.database import get_db
from app.latency_metrics import tracker as latency_tracker, LatencySummary, PublicLatencySample
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
    KadiCase,
    KadiCaseDocument,
    KadiEntity,
    KadiModuleInsight,
    KadiResolutionDecision,
    KadiThresholdCalibration,
)
# OCR parser and extraction agent from kadi shared layer
from kadi.fhir_import import FhirBundleError, parse_fhir_bundle
from kadi.graph import CaseGraph, EntityRecord, PendingLink, StayInfo, build_case_graph
from kadi.resolution import RESOLVABLE_ENTITY_TYPES, ResolutionThresholds
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
# --- Route Implementations ----------------------------------------------------

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
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
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
