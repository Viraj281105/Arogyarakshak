"""
SQLAlchemy Models.

Database tables for Kadi shared context (cases and entities).
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, Boolean, ForeignKey, Table, JSON, LargeBinary
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
    """Represents an insurance claim dispute dossier."""

    __tablename__ = "bimanyay_cases"

    id = Column(String, primary_key=True, index=True)
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
    """Represents a multi-tier statutory grievance tracking record."""

    __tablename__ = "bimanyay_grievances"

    id = Column(String, primary_key=True, index=True)
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
