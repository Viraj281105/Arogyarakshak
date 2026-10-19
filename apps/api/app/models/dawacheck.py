"""DawaCheck: learned brand -> generic mappings."""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Float,
)

from app.database import Base


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
