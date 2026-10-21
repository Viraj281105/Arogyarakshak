"""Human OCR transcription (ADR-011): tasks, assignments, blind readings."""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Float,
    Boolean,
    ForeignKey,
    Integer,
    JSON,
    UniqueConstraint,
)

from app.database import Base


class KadiTranscriptionTask(Base):
    """An uncertain OCR reading awaiting human transcription. Stores no image (ADR-003):
    only a redacted candidate, a redacted masked context line and a location hint."""

    __tablename__ = "kadi_transcription_tasks"

    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_id = Column(String, nullable=True, index=True)
    source = Column(String, nullable=False)  # OCR_LOW_CONFIDENCE | CASE_HOLDER_FLAGGED
    field_type = Column(String, nullable=False)
    risk_level = Column(String, nullable=False)
    required_reviews = Column(Integer, nullable=False)
    ocr_candidate = Column(String, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    masked_context = Column(String, nullable=False)
    location_hint = Column(JSON, nullable=True)
    status = Column(String, nullable=False)
    final_value = Column(String, nullable=True)
    resolution_reason = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    consent_confirmed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KadiTranscriptionAssignment(Base):
    __tablename__ = "kadi_transcription_assignments"
    __table_args__ = (UniqueConstraint("task_id", "reviewer_id", name="uq_kadi_transcription_assignment"),)

    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("kadi_transcription_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(String, ForeignKey("kadi_clinical_reviewers.id"), nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)


class KadiTranscriptionSubmission(Base):
    """One independent human reading. One per reviewer per task, enforced by the DB."""

    __tablename__ = "kadi_transcription_submissions"
    __table_args__ = (UniqueConstraint("task_id", "reviewer_id", name="uq_kadi_transcription_submission"),)

    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("kadi_transcription_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(String, ForeignKey("kadi_clinical_reviewers.id"), nullable=False)
    value = Column(String, nullable=True)
    unreadable = Column(Boolean, nullable=False, default=False)
    reviewer_confidence = Column(String, nullable=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
