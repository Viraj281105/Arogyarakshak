"""
Kadi API Endpoints.

Case creation, document uploads (OCR parsing), entity extraction and resolution (#31),
ABDM/FHIR record import (#54), resolution feedback and threshold calibration (#88), the
case knowledge graph (#86) and auto-triggered module insights (#32).

One module per route group; this package composes their routers into ``router`` (mounted
at /api/v1/kadi). The re-exports below keep earlier ``from app.api.v1.endpoints.kadi import
...`` imports working; new code should import from ``app.services`` instead.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.kadi import abdm, cases, insights, resolution
from app.api.v1.endpoints.kadi.cases import ALLOWED_UPLOAD_EXTENSIONS  # noqa: F401
from app.api.v1.endpoints.kadi.schemas import (  # noqa: F401
    CaseCreate,
    CaseResponse,
    CaseCreatedResponse,
    EntityResponse,
    CaseDetailResponse,
    ResolutionDecisionResponse,
    ResolutionFeedbackRequest,
    CalibrationAttempt,
    ResolutionFeedbackResponse,
    AbdmImportResponse,
    _decision_response,
)
from app.config import settings  # noqa: F401 — tests patch settings through this module
from app.latency_metrics import tracker as latency_tracker  # noqa: F401
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

router = APIRouter()
for _group in (cases, resolution, insights, abdm):
    router.include_router(_group.router)
