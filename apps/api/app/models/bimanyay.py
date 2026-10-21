"""BimaNyay: claim-denial disputes, grievances and their SLA timeline."""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Float,
    Boolean,
    ForeignKey,
)

from app.database import Base


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
