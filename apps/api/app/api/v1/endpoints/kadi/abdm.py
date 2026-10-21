"""ABDM / FHIR record import (#54)."""

from datetime import date, datetime
from typing import Optional
import hashlib
import uuid
import logging
import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auto_triggers import run_auto_triggers
from app.config import settings
from app.case_auth import require_case_access
from app.consent import require_case_consent
from app.database import get_db
from app.kadi_resolution import (
    MentionInput,
    resolve_and_attach,
)
from app.models import (
    KadiCase,
    KadiCaseDocument,
)
from kadi.fhir_import import FhirBundleError, parse_fhir_bundle
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
    AbdmImportResponse,
)
from app.api.v1.endpoints.kadi.loaders import _load_case_with_entities

logger = logging.getLogger("arogyarakshak.api.kadi")
router = APIRouter()


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
