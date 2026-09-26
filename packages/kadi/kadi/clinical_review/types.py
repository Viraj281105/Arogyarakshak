"""
Shared vocabulary for the clinical-review layer (ADR-011).

Everything here is DB-agnostic. The API persists these values as plain strings, so an
enum member's `.value` is the stored/serialized form.
"""

from datetime import datetime
from enum import Enum
from typing import Optional


class ProvenanceClass(str, Enum):
    """Where a piece of case context came from. Must survive every downstream hop."""

    # Produced by ArogyaRakshak software — OCR, LLM extraction, or a rule engine. Never
    # the judgment of a named human.
    AI_DERIVED = "AI_DERIVED"
    # A machine-derived or document-derived fact that a named human reviewer confirmed,
    # rejected, or transcribed.
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    # Content written by a named human reviewer in their own words.
    HUMAN_AUTHORED = "HUMAN_AUTHORED"
    # A published reference the software compared against (CGHS rates, a curated code
    # table). Its own source/version travels with it.
    EXTERNAL_SOURCE = "EXTERNAL_SOURCE"
    # Typed in by the case holder (patient or representative), e.g. an insurer's denial
    # reason copied from a letter. Not verified by anyone.
    PATIENT_PROVIDED = "PATIENT_PROVIDED"


PROVENANCE_DESCRIPTIONS = {
    ProvenanceClass.AI_DERIVED: (
        "Machine-derived: produced by ArogyaRakshak software (OCR, LLM extraction or a rule "
        "engine). Not the opinion of any named person."
    ),
    ProvenanceClass.HUMAN_REVIEWED: (
        "Human-reviewed: a named reviewer confirmed, rejected or transcribed this item."
    ),
    ProvenanceClass.HUMAN_AUTHORED: (
        "Human-authored: written by a named reviewer as their own professional statement."
    ),
    ProvenanceClass.EXTERNAL_SOURCE: (
        "External source: a published reference used for comparison; see its cited source."
    ),
    ProvenanceClass.PATIENT_PROVIDED: (
        "Patient-provided: entered by the case holder; not verified by ArogyaRakshak or a reviewer."
    ),
}


class ReviewerCategory(str, Enum):
    DOCTOR = "DOCTOR"
    PHARMACIST = "PHARMACIST"
    MEDICAL_TRANSCRIPTIONIST = "MEDICAL_TRANSCRIPTIONIST"
    TRAINED_ANNOTATOR = "TRAINED_ANNOTATOR"


REVIEWER_CATEGORY_LABELS = {
    ReviewerCategory.DOCTOR: "Doctor",
    ReviewerCategory.PHARMACIST: "Pharmacist",
    ReviewerCategory.MEDICAL_TRANSCRIPTIONIST: "Medical transcriptionist",
    ReviewerCategory.TRAINED_ANNOTATOR: "Trained annotator",
}

# Only these categories may author a clinical statement or confirm a clinical fact.
# Transcription is deliberately open to every category: reading handwriting does not
# require a medical degree, and calling a transcriptionist a "doctor" would misstate who
# did the work.
CLINICAL_JUDGMENT_CATEGORIES = frozenset({ReviewerCategory.DOCTOR})
CLINICAL_JUDGMENT_CATEGORIES_VALUES = frozenset(c.value for c in CLINICAL_JUDGMENT_CATEGORIES)


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    SELF_DECLARED = "SELF_DECLARED"
    DEMO_VERIFIED = "DEMO_VERIFIED"
    EXTERNALLY_VERIFIED = "EXTERNALLY_VERIFIED"


def verification_label(
    status: str,
    source: Optional[str] = None,
    verified_at: Optional[datetime] = None,
) -> str:
    """The only wording any client should show for a reviewer's verification state.

    Centralised so no surface can drift into "Verified Doctor" for a reviewer whose
    registration nobody actually checked.
    """
    if status == VerificationStatus.EXTERNALLY_VERIFIED.value:
        when = f" on {verified_at.date().isoformat()}" if verified_at else ""
        return f"Registration verified against {source or 'an external registry'}{when}"
    if status == VerificationStatus.DEMO_VERIFIED.value:
        return "Demo verification only — not checked against any real medical registry"
    if status == VerificationStatus.SELF_DECLARED.value:
        return "Self-declared registration — not verified by ArogyaRakshak"
    return "Identity and registration not verified"


class ConflictOfInterest(str, Enum):
    TREATING_DOCTOR = "TREATING_DOCTOR"
    HOSPITAL_AFFILIATED = "HOSPITAL_AFFILIATED"
    INSURER_AFFILIATED = "INSURER_AFFILIATED"
    INDEPENDENT_REVIEWER = "INDEPENDENT_REVIEWER"
    OTHER = "OTHER"


COI_LABELS = {
    ConflictOfInterest.TREATING_DOCTOR: "Treating doctor for this patient",
    ConflictOfInterest.HOSPITAL_AFFILIATED: "Affiliated with the treating hospital",
    ConflictOfInterest.INSURER_AFFILIATED: "Affiliated with the insurer",
    ConflictOfInterest.INDEPENDENT_REVIEWER: "Declares no relationship with the patient, hospital or insurer",
    ConflictOfInterest.OTHER: "Other relationship (see disclosure)",
}


class ReviewType(str, Enum):
    # A reviewer writes an attributable professional statement answering a question.
    CLINICAL_STATEMENT = "CLINICAL_STATEMENT"
    # A reviewer confirms or rejects specific clinical facts a workflow depends on.
    FACT_CONFIRMATION = "FACT_CONFIRMATION"


class ReviewStatus(str, Enum):
    REQUESTED = "REQUESTED"
    ASSIGNED = "ASSIGNED"
    IN_REVIEW = "IN_REVIEW"
    COMPLETED = "COMPLETED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"


class StatementStatus(str, Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    FINALIZED = "FINALIZED"
    SUPERSEDED = "SUPERSEDED"
    # Revocation: the author retracted a finalized statement. Its text stays in the
    # audit record; no package may present it as a current opinion.
    WITHDRAWN = "WITHDRAWN"


class FactDecision(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CANNOT_DETERMINE = "CANNOT_DETERMINE"


class SourceModule(str, Enum):
    BILLNYAY = "billnyay"
    BIMANYAY = "bimanyay"
    DAAVISETU = "daavisetu"
    DAWACHECK = "dawacheck"
    KADI = "kadi"


class ReviewTrigger(str, Enum):
    MANUAL = "MANUAL"
    PLAUSIBILITY_FLAG = "PLAUSIBILITY_FLAG"
    DENIAL_CATEGORY = "DENIAL_CATEGORY"
    SAFETY_RULE = "SAFETY_RULE"
    READINESS_CLINICAL_FACT = "READINESS_CLINICAL_FACT"


class ActorType(str, Enum):
    CASE_HOLDER = "CASE_HOLDER"
    REVIEWER = "REVIEWER"
    GOVERNANCE_ADMIN = "GOVERNANCE_ADMIN"
    INSTITUTION = "INSTITUTION"
    SYSTEM = "SYSTEM"


class AuditEventType(str, Enum):
    REVIEWER_REGISTERED = "REVIEWER_REGISTERED"
    REVIEWER_VERIFICATION_ATTEMPTED = "REVIEWER_VERIFICATION_ATTEMPTED"
    REVIEWER_BOARD_SEAT_CHANGED = "REVIEWER_BOARD_SEAT_CHANGED"
    REVIEWER_DEACTIVATED = "REVIEWER_DEACTIVATED"
    REVIEW_REQUESTED = "REVIEW_REQUESTED"
    REVIEWER_ASSIGNED = "REVIEWER_ASSIGNED"
    REVIEW_ACCEPTED = "REVIEW_ACCEPTED"
    REVIEW_DECLINED = "REVIEW_DECLINED"
    REVIEW_CANCELLED = "REVIEW_CANCELLED"
    COI_DECLARED = "COI_DECLARED"
    EVIDENCE_ACCESSED = "EVIDENCE_ACCESSED"
    STATEMENT_CREATED = "STATEMENT_CREATED"
    STATEMENT_EDITED = "STATEMENT_EDITED"
    STATEMENT_SUBMITTED = "STATEMENT_SUBMITTED"
    STATEMENT_FINALIZED = "STATEMENT_FINALIZED"
    STATEMENT_SUPERSEDED = "STATEMENT_SUPERSEDED"
    STATEMENT_WITHDRAWN = "STATEMENT_WITHDRAWN"
    FACT_DECIDED = "FACT_DECIDED"
    RULE_PROPOSED = "RULE_PROPOSED"
    RULE_EDITED = "RULE_EDITED"
    RULE_SUBMITTED = "RULE_SUBMITTED"
    RULE_APPROVED = "RULE_APPROVED"
    RULE_REJECTED = "RULE_REJECTED"
    RULE_ACTIVATED = "RULE_ACTIVATED"
    RULE_SUPERSEDED = "RULE_SUPERSEDED"
    RULE_RETIRED = "RULE_RETIRED"
    TRANSCRIPTION_REQUESTED = "TRANSCRIPTION_REQUESTED"
    TRANSCRIPTION_ASSIGNED = "TRANSCRIPTION_ASSIGNED"
    TRANSCRIPTION_SUBMITTED = "TRANSCRIPTION_SUBMITTED"
    TRANSCRIPTION_CONFIRMED = "TRANSCRIPTION_CONFIRMED"
    TRANSCRIPTION_REJECTED = "TRANSCRIPTION_REJECTED"
    TRANSCRIPTION_CANCELLED = "TRANSCRIPTION_CANCELLED"


# The floor disclaimer every user-facing safety surface must carry.
SAFETY_FLOOR_DISCLAIMER = (
    "This safety layer is a decision-support floor, not a substitute for professional "
    "clinical assessment."
)
