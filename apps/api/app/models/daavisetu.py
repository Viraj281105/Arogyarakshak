"""DaaviSetu: pre-authorisation claims, institutions and private playbooks."""

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
    JSON,
    UniqueConstraint,
)

from app.database import Base


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
