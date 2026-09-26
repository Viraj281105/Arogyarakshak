"""
Kadi clinical-review layer (ADR-011): the DB-agnostic rules behind human clinical review,
safety governance and human OCR resolution. Persistence lives in apps/api
(`app/clinical/`), mirroring how `kadi.resolution` pairs with `app/kadi_resolution.py`.

The organising principle: machine-derived evidence and accountable human judgment are
different kinds of thing, and the difference must survive every downstream step.
"""

from .types import (
    CLINICAL_JUDGMENT_CATEGORIES_VALUES,
    PROVENANCE_DESCRIPTIONS,
    SAFETY_FLOOR_DISCLAIMER,
    ActorType,
    AuditEventType,
    ConflictOfInterest,
    COI_LABELS,
    FactDecision,
    ProvenanceClass,
    REVIEWER_CATEGORY_LABELS,
    ReviewerCategory,
    ReviewStatus,
    ReviewTrigger,
    ReviewType,
    SourceModule,
    StatementStatus,
    VerificationStatus,
    verification_label,
)

__all__ = [
    "CLINICAL_JUDGMENT_CATEGORIES_VALUES",
    "PROVENANCE_DESCRIPTIONS",
    "SAFETY_FLOOR_DISCLAIMER",
    "ActorType",
    "AuditEventType",
    "ConflictOfInterest",
    "COI_LABELS",
    "FactDecision",
    "ProvenanceClass",
    "REVIEWER_CATEGORY_LABELS",
    "ReviewerCategory",
    "ReviewStatus",
    "ReviewTrigger",
    "ReviewType",
    "SourceModule",
    "StatementStatus",
    "VerificationStatus",
    "verification_label",
]
