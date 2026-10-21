"""SchemeSetu: consent-bounded income profile per case."""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Float,
    ForeignKey,
)

from app.database import Base


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
