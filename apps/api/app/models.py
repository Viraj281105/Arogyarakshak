"""
SQLAlchemy Models.

Database tables for Kadi shared context (cases and entities).
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, Boolean, ForeignKey, Table, JSON
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

