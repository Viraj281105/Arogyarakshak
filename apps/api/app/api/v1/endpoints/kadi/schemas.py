"""Request/response schemas for the Kadi routes."""

from typing import Any, Dict, List, Optional
import logging

from pydantic import BaseModel, Field, ConfigDict

from app.models import (
    KadiResolutionDecision,
)
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
