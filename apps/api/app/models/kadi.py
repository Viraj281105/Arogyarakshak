"""Kadi case core: cases, entities, documents, processing jobs, resolution, insights."""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Float,
    Boolean,
    ForeignKey,
    Integer,
    Table,
    JSON,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


# Association Table linking KadiCase and KadiEntity
kadi_case_entities = Table(
    "kadi_case_entities",
    Base.metadata,
    Column("case_id", String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), primary_key=True),
    Column("entity_id", String, ForeignKey("kadi_entities.id", ondelete="CASCADE"), primary_key=True),
    Column("source_document", String, nullable=True),
    Column("source_module", String, nullable=True),
)


class KadiCase(Base):
    """Represents a patient case/session."""

    __tablename__ = "kadi_cases"

    id = Column(String, primary_key=True, index=True)
    date_admission = Column(DateTime, nullable=True)
    date_discharge = Column(DateTime, nullable=True)
    total_charged = Column(Float, default=0.0)
    status = Column(String, default="active")  # active, completed, archived
    consent_opt_in = Column(Boolean, default=False)
    # SHA-256 hash of a per-case access token, generated once at creation and returned to
    # the caller only in that response (see app/case_auth.py, ADR-009). The plaintext
    # token is never stored. Nullable only so schema creation never fails on a stray old
    # row from before this column existed — app.case_auth.require_case_access treats a
    # null/empty hash as "this case can never be authorized" rather than "open access".
    access_token_hash = Column(String, nullable=True)
    # SEC-03: server-side retention deadline, set at creation independent of whether the
    # client ever comes back with its access token. Before this, a case (and everything
    # derived from it) persisted forever unless its own token holder explicitly called
    # DELETE /cases/{id} — a client that simply lost its one-time token (closed the tab,
    # lost the app's in-memory store, uninstalled the app) had no way to ever trigger
    # deletion again, so the data was retained permanently by default. Nullable only so
    # schema creation never fails on a stray pre-existing row; app.case_retention treats
    # a null expires_at as already-expired (never as "keep forever").
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    entities = relationship("KadiEntity", secondary=kadi_case_entities, back_populates="cases")


class KadiEntity(Base):
    """Represents a structured fact/entity extracted from patient documents."""

    __tablename__ = "kadi_entities"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String, index=True)  # medicine, procedure, hospital, cost, diagnosis
    value = Column(String, nullable=True)
    meta = Column(JSON, nullable=True)  # stores extra fields such as generic alternatives, dosage, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    cases = relationship("KadiCase", secondary=kadi_case_entities, back_populates="entities")


class KadiCaseDocument(Base):
    """Fingerprint of a document already ingested into a case (duplicate-upload guard).

    Re-uploading the same bill used to duplicate every entity and add its total to
    `total_charged` a second time. Only the SHA-256 digest and the extension are stored —
    never the file, its text or its name, which could itself identify the patient (ADR-003).
    """

    __tablename__ = "kadi_case_documents"
    __table_args__ = (UniqueConstraint("case_id", "sha256", name="uq_kadi_case_document_digest"),)

    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    sha256 = Column(String(64), nullable=False)
    extension = Column(String, nullable=True)
    source = Column(String, nullable=False, default="upload")  # upload | abdm_fhir
    created_at = Column(DateTime, default=datetime.utcnow)


class KadiDocumentJob(Base):
    """Processing state of one uploaded document (ADR-019).

    The live progress stream (``app.services.case_ingestion.processing_status``) is
    in-memory, so a restart used to leave a case looking idle, as if nothing had been
    uploaded. This row survives: on start-up, rows still ``queued``/``processing`` are
    marked ``interrupted`` so the client is told to upload again. Only the digest is kept
    — never the file, its text or its name (ADR-003) — so an interrupted job cannot be
    retried server-side; the patient re-uploads.
    """

    __tablename__ = "kadi_document_jobs"
    __table_args__ = (
        CheckConstraint(
            "state IN ('queued', 'processing', 'completed', 'duplicate', 'failed', 'interrupted')",
            name="ck_kadi_document_jobs_state",
        ),
    )

    id = Column(String, primary_key=True)
    case_id = Column(String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    sha256 = Column(String(64), nullable=False)
    state = Column(String, nullable=False)
    # Version of the ingestion pipeline that handled the document, for provenance.
    pipeline_version = Column(String, nullable=False)
    # Correlates with the server log line for a failure; never the exception text.
    error_id = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)


class KadiResolutionDecision(Base):
    """An entity-resolution decision that needs (or received) a human answer (#31, #88).

    One row per MERGE (status `auto_merged`) and per ASK (status `pending`). NEW decisions
    are not stored. `mention_payload` keeps the merged mention's name/value/meta so an
    automatic merge can be split back out if the user says it was wrong.
    """

    __tablename__ = "kadi_resolution_decisions"

    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)  # MERGE | ASK
    # auto_merged | pending | confirmed | rejected | split
    status = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False, default="upload")  # upload | abdm_fhir
    mention_entity_id = Column(String, nullable=True)  # the separately kept entity (ASK only)
    candidate_entity_id = Column(String, nullable=False)
    candidate_name = Column(String, nullable=False)
    mention_payload = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=False)
    signals = Column(JSON, nullable=False)
    reasons = Column(JSON, nullable=False)
    thresholds = Column(JSON, nullable=False)
    feedback_same_entity = Column(Boolean, nullable=True)
    feedback_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class KadiThresholdCalibration(Base):
    """Snapshot of a feedback recalibration attempt (#88). Aggregate numbers only."""

    __tablename__ = "kadi_threshold_calibrations"

    id = Column(String, primary_key=True, index=True)
    scope = Column(String, nullable=False, index=True)  # entity type, or "all_types"
    status = Column(String, nullable=False)  # CALIBRATED | INSUFFICIENT_EVIDENCE
    merge_threshold = Column(Float, nullable=False)
    ask_threshold = Column(Float, nullable=False)
    sample_count = Column(Integer, nullable=False)
    metrics = Column(JSON, nullable=False)
    reasons = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class KadiModuleInsight(Base):
    """Latest result of a module check Kadi fired automatically for a case (#32, #92)."""

    __tablename__ = "kadi_module_insights"
    __table_args__ = (UniqueConstraint("case_id", "module_check", name="uq_kadi_module_insight"),)

    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    module_check = Column(String, nullable=False)
    # COMPLETED | FAILED | NOT_READY
    status = Column(String, nullable=False)
    trigger = Column(String, nullable=False)  # document_processed | abdm_import | income_profile_updated
    summary = Column(JSON, nullable=True)
    missing_context = Column(JSON, nullable=True)
    error_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
