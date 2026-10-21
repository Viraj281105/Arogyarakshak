"""Clinical review (ADR-011): reviewers, reviews, statements, fact confirmations, audit trail."""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Integer,
    JSON,
)

from app.database import Base


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
