"""Clinical safety governance (ADR-011): rules, approvals, scan results."""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    Integer,
    JSON,
    UniqueConstraint,
)

from app.database import Base


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


class KadiSafetyScanResult(Base):
    """A safety rule that matched an uploaded document's FULL text at upload time.

    Only the rule id/version and the matched rule terms are stored — never any document
    text — so red flags beyond the 1,000-character excerpt are not lost (ADR-003/011)."""

    __tablename__ = "kadi_safety_scan_results"

    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("kadi_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(String, nullable=False, index=True)
    rule_version = Column(Integer, nullable=False)
    matched_terms = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
