"""
SQLAlchemy Models.

Database tables for Kadi shared context (cases and entities).
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Date,
    DateTime,
    Float,
    Boolean,
    ForeignKey,
    Integer,
    Table,
    JSON,
    LargeBinary,
    UniqueConstraint,
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


class SchemeSetuCaseProfile(Base):
    """Consent-bounded income profile for a case (#92).

    Only the two facts the eligibility rules evaluate are stored. Social category is not:
    the engine does not evaluate it, so keeping it would be collection without purpose.
    The patient can delete the profile at any time.
    """

    __tablename__ = "schemesetu_case_profiles"

    case_id = Column(String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), primary_key=True)
    annual_income_inr = Column(Float, nullable=False)
    state = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DawaCheckGenericMapping(Base):
    """Represents Brand-to-Generic formulation mappings and ceiling prices."""

    __tablename__ = "dawacheck_generic_mappings"

    id = Column(String, primary_key=True, index=True)
    brand_name = Column(String, index=True, nullable=False)
    generic_name = Column(String, index=True, nullable=False)  # active ingredient
    dosage = Column(String, nullable=True)  # e.g., "650mg"
    ceiling_price = Column(Float, nullable=True)  # ceiling price from NPPA
    mrp = Column(Float, nullable=True)  # brand's MRP
    created_at = Column(DateTime, default=datetime.utcnow)


class BimaNyayCase(Base):
    """Represents an insurance claim dispute dossier.

    SEC-04: `case_id` optionally links this dispute record to a Kadi case (ADR-009's
    access-token-authorized case). Nullable — BimaNyay can still be used stand-alone
    (its own screen has no case-creation flow), but when a case_id IS supplied, the
    caller must hold that case's access token (app.case_auth) and consent
    (app.consent) before the record is created, and the record is cascade-deleted with
    its case (ondelete=CASCADE), exactly like every other module's case-linked data."""

    __tablename__ = "bimanyay_cases"

    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), nullable=True, index=True)
    policy_number = Column(String, index=True, nullable=False)
    insurer_name = Column(String, index=True, nullable=False)
    policy_age_years = Column(Float, default=0.0)
    claimed_amount = Column(Float, default=0.0)
    denied_amount = Column(Float, default=0.0)
    denial_category = Column(String, nullable=False)
    denial_reason_raw = Column(String, nullable=False)
    diagnosis = Column(String, nullable=False)
    is_wrongful = Column(Boolean, default=False)
    reversal_probability = Column(Float, default=0.0)
    primary_grounds = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BimaNyayGrievance(Base):
    """Represents a multi-tier statutory grievance tracking record.

    SEC-04: same optional case_id linkage as BimaNyayCase above."""

    __tablename__ = "bimanyay_grievances"

    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), nullable=True, index=True)
    claim_number = Column(String, index=True, nullable=True)
    insurer_name = Column(String, index=True, nullable=False)
    current_tier = Column(String, default="LEVEL_1_GRO")
    date_initiated = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BimaNyayTimelineEvent(Base):
    """Milestone event in the grievance escalation SLA tracker."""

    __tablename__ = "bimanyay_timeline_events"

    id = Column(String, primary_key=True, index=True)
    grievance_id = Column(String, ForeignKey("bimanyay_grievances.id", ondelete="CASCADE"), nullable=False)
    tier = Column(String, nullable=False)
    title = Column(String, nullable=False)
    deadline_date = Column(String, nullable=False)
    status = Column(String, default="PENDING")
    instructions = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)




class BillNyayAppeal(Base):
    """Persisted appeal letter + its compiled PDF and integrity signature (#66).

    The appeal letter is LLM-drafted (or template-fallback) and can differ between
    calls to POST .../appeal, so the PDF download and integrity verification must
    render/check the exact bytes generated at draft time — not a value regenerated
    later, which could silently differ. One row per case; re-drafting replaces it.
    """

    __tablename__ = "billnyay_appeals"

    id = Column(String, primary_key=True, index=True)
    case_id = Column(
        String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    appeal_letter = Column(String, nullable=False)
    pdf_bytes = Column(LargeBinary, nullable=False)
    sha256_hash = Column(String, nullable=False)
    hmac_signature = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DaaviSetuClaim(Base):
    """Pre-authorization claim submitted for a case.

    The submitted form is the document the patient reviews and signs, so it must be
    stored verbatim. Previously the POST returned the claim without persisting it and the
    PDF download rebuilt a *different* ClaimData from Kadi entities, fabricating the
    policy number and defaulting the patient name to "Patient".

    One claim per case: `case_id` is unique, and re-submitting updates the same row.
    """

    __tablename__ = "daavisetu_claims"

    id = Column(String, primary_key=True, index=True)  # claim_id, e.g. CLAIM-a1b2c3d4
    case_id = Column(
        String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # Submitted form fields — authoritative for PDF rendering.
    policy_number = Column(String, nullable=False)
    patient_name = Column(String, nullable=False)
    hospital_name = Column(String, nullable=False)
    diagnosis = Column(String, nullable=False)
    estimated_cost = Column(Float, default=0.0)
    treatment_plan = Column(String, nullable=False)
    # Policyholder-declared sum insured (#84). Nullable: policy-limit validation is
    # skipped, never assumed, when the policyholder hasn't supplied a limit.
    sum_insured = Column(Float, nullable=True)

    status = Column(String, default="ready_for_review")  # ready_for_review, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =====================================================================================
# Clinical review, safety governance and human OCR resolution (ADR-011).
#
# Global records (reviewers, safety rules, institutions, playbooks) outlive any one case.
# Every case-scoped record carries case_id and is removed by app.clinical.purge when the
# case is deleted or expires. Rules live in packages/kadi/kadi/clinical_review.
# =====================================================================================


class KadiClinicalReviewer(Base):
    """A named human reviewer. No login system exists (ADR-008/009): the reviewer holds a
    bearer credential shown once at registration; only its SHA-256 hash is stored."""

    __tablename__ = "kadi_clinical_reviewers"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    designation = Column(String, nullable=True)
    category = Column(String, nullable=False)  # ReviewerCategory
    specialty = Column(String, nullable=True)
    registration_number = Column(String, nullable=True)
    registration_authority = Column(String, nullable=True)
    # UNVERIFIED | SELF_DECLARED | DEMO_VERIFIED | EXTERNALLY_VERIFIED. Self-registration
    # can never set more than SELF_DECLARED.
    verification_status = Column(String, nullable=False)
    verification_source = Column(String, nullable=True)
    verification_timestamp = Column(DateTime, nullable=True)
    affiliation = Column(String, nullable=True)
    # Standing, case-independent disclosures (e.g. "empanelled with insurer X"). The
    # case-specific conflict of interest is declared per review.
    standing_disclosures = Column(String, nullable=True)
    reviewer_notes = Column(String, nullable=True)
    credential_hash = Column(String, nullable=False, unique=True, index=True)
    is_safety_board_member = Column(Boolean, nullable=False, default=False)
    is_demo = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KadiClinicalReview(Base):
    """A consented request for human review of one case. The evidence packet is frozen at
    request time and is the only case data the assigned reviewer can ever see."""

    __tablename__ = "kadi_clinical_reviews"

    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    source_module = Column(String, nullable=False)
    review_type = Column(String, nullable=False)  # CLINICAL_STATEMENT | FACT_CONFIRMATION
    status = Column(String, nullable=False)
    clinical_question = Column(String, nullable=False)
    trigger = Column(String, nullable=False, default="MANUAL")
    trigger_ref = Column(String, nullable=True)
    evidence_scope = Column(JSON, nullable=False)
    evidence_packet = Column(JSON, nullable=False)
    coi_context = Column(JSON, nullable=False)
    insurer_name = Column(String, nullable=True)
    consent_confirmed_at = Column(DateTime, nullable=False)
    assigned_reviewer_id = Column(String, ForeignKey("kadi_clinical_reviewers.id"), nullable=True, index=True)
    assigned_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    coi_category = Column(String, nullable=True)
    coi_disclosure = Column(String, nullable=True)
    coi_declared_at = Column(DateTime, nullable=True)
    decline_reason = Column(String, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KadiClinicalStatement(Base):
    """A reviewer's own professional statement. Immutable once FINALIZED: changes create a
    new version and the old one becomes SUPERSEDED. Stored provenance: HUMAN_AUTHORED."""

    __tablename__ = "kadi_clinical_statements"

    id = Column(String, primary_key=True, index=True)
    review_id = Column(String, ForeignKey("kadi_clinical_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(String, ForeignKey("kadi_clinical_reviewers.id"), nullable=False, index=True)
    statement_version = Column(Integer, nullable=False, default=1)
    supersedes_statement_id = Column(String, nullable=True)
    clinical_question = Column(String, nullable=False)
    evidence_reviewed = Column(JSON, nullable=False)
    reviewer_statement = Column(String, nullable=False)
    limitations = Column(String, nullable=False)
    coi_category = Column(String, nullable=False)
    coi_disclosure = Column(String, nullable=True)
    reviewer_snapshot = Column(JSON, nullable=True)  # frozen at finalization
    status = Column(String, nullable=False)
    confirmation_text = Column(String, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    content_sha256 = Column(String, nullable=True)
    withdrawn_reason = Column(String, nullable=True)
    withdrawn_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    finalized_at = Column(DateTime, nullable=True)


class KadiClinicalFactConfirmation(Base):
    """One clinical fact a workflow depends on (e.g. a DaaviSetu readiness item), for a
    reviewer to confirm, reject or mark as not determinable. Provenance: HUMAN_REVIEWED."""

    __tablename__ = "kadi_clinical_fact_confirmations"

    id = Column(String, primary_key=True, index=True)
    review_id = Column(String, ForeignKey("kadi_clinical_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    fact_key = Column(String, nullable=False)
    fact_question = Column(String, nullable=False)
    source = Column(String, nullable=False)  # daavisetu_readiness
    playbook_ref = Column(String, nullable=True)
    decision = Column(String, nullable=False, default="PENDING")
    reviewer_id = Column(String, ForeignKey("kadi_clinical_reviewers.id"), nullable=True)
    reviewer_note = Column(String, nullable=True)
    reviewer_snapshot = Column(JSON, nullable=True)
    coi_category = Column(String, nullable=True)
    coi_disclosure = Column(String, nullable=True)
    confirmation_text = Column(String, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class KadiClinicalAuditEvent(Base):
    """Append-only audit trail. `details` carries ids, statuses and counts only — never
    statement text, evidence values or document content (app.clinical.audit enforces it).
    case_id is null for global events (safety rules, reviewer registry)."""

    __tablename__ = "kadi_clinical_audit_events"

    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), nullable=True, index=True)
    review_id = Column(String, nullable=True, index=True)
    subject_type = Column(String, nullable=False)
    subject_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    actor_type = Column(String, nullable=False)
    actor_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class KadiSafetyRule(Base):
    """A versioned red-flag escalation rule adapted from a published protocol. Immutable
    once APPROVED; ACTIVE only after independent approval by named board members."""

    __tablename__ = "kadi_safety_rules"
    __table_args__ = (UniqueConstraint("rule_key", "version", name="uq_kadi_safety_rule_version"),)

    id = Column(String, primary_key=True, index=True)
    rule_key = Column(String, nullable=False, index=True)
    version = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    trigger = Column(JSON, nullable=False)
    action = Column(JSON, nullable=False)
    source_name = Column(String, nullable=False)
    source_reference = Column(String, nullable=True)
    source_version = Column(String, nullable=True)
    source_section = Column(String, nullable=True)
    limitations = Column(String, nullable=False)
    status = Column(String, nullable=False)
    proposed_by = Column(String, ForeignKey("kadi_clinical_reviewers.id"), nullable=False)
    required_approvals = Column(Integer, nullable=False, default=1)
    effective_date = Column(Date, nullable=True)
    review_due_date = Column(Date, nullable=False)
    changelog = Column(String, nullable=True)
    supersedes_rule_id = Column(String, nullable=True)
    submitted_content_sha256 = Column(String, nullable=True)
    is_demo = Column(Boolean, nullable=False, default=False)
    activated_at = Column(DateTime, nullable=True)
    activated_by = Column(String, nullable=True)
    retired_at = Column(DateTime, nullable=True)
    retired_by = Column(String, nullable=True)
    retired_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KadiSafetyRuleApproval(Base):
    """An attributable approve/reject decision on one exact submitted content hash —
    editing a rule after approval invalidates earlier approvals."""

    __tablename__ = "kadi_safety_rule_approvals"
    __table_args__ = (
        UniqueConstraint("rule_id", "reviewer_id", "content_sha256", name="uq_kadi_safety_rule_approval"),
    )

    id = Column(String, primary_key=True, index=True)
    rule_id = Column(String, ForeignKey("kadi_safety_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(String, ForeignKey("kadi_clinical_reviewers.id"), nullable=False)
    decision = Column(String, nullable=False)  # APPROVE | REJECT
    comment = Column(String, nullable=True)
    content_sha256 = Column(String, nullable=False)
    reviewer_snapshot = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


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


class DaaviSetuInstitution(Base):
    """A hospital insurance desk that keeps private, internal preauth guidance. Holds a
    bearer credential (hash only); its playbooks are invisible to every other institution."""

    __tablename__ = "daavisetu_institutions"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    credential_hash = Column(String, nullable=False, unique=True, index=True)
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class DaaviSetuPlaybook(Base):
    """Institution-internal documentation guidance for one insurer + procedure category.
    Lists documentation commonly requested; never asserts case facts or approval effects.
    Immutable once ACTIVE: changes create a new version."""

    __tablename__ = "daavisetu_playbooks"
    __table_args__ = (
        UniqueConstraint("institution_id", "playbook_key", "version", name="uq_daavisetu_playbook_version"),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("daavisetu_institutions.id"), nullable=False, index=True)
    playbook_key = Column(String, nullable=False, index=True)
    version = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    insurer = Column(String, nullable=False)
    policy_product = Column(String, nullable=True)
    procedure_category = Column(String, nullable=False)
    items = Column(JSON, nullable=False)
    commonly_requested_evidence = Column(JSON, nullable=False)
    internal_notes = Column(String, nullable=True)
    source_provenance = Column(String, nullable=False)
    owner = Column(String, nullable=False)
    effective_date = Column(Date, nullable=False)
    review_due_date = Column(Date, nullable=False)
    status = Column(String, nullable=False)  # DRAFT | ACTIVE | SUPERSEDED | RETIRED
    supersedes_playbook_id = Column(String, nullable=True)
    activated_at = Column(DateTime, nullable=True)
    retired_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
