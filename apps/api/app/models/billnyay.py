"""BillNyay: drafted, signed appeal PDFs."""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    LargeBinary,
)

from app.database import Base


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
