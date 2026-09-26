"""Response shapes for the clinical-review layer (ADR-011).

One place decides what each audience may see:
- public reviewer profile: never the credential hash, notes, or demo flags beyond the label;
- case holder: review status and PUBLISHED statements only (drafts are the reviewer's own);
- reviewer: their own drafts plus the frozen evidence packet, after declaring COI.
Every human output carries its provenance class.
"""

from typing import Any, Dict, List, Optional

from kadi.clinical_review import (
    COI_LABELS,
    PROVENANCE_DESCRIPTIONS,
    REVIEWER_CATEGORY_LABELS,
    ConflictOfInterest,
    ProvenanceClass,
    ReviewerCategory,
    verification_label,
)
from kadi.clinical_review.lifecycle import PUBLISHED_STATEMENT_STATES

from app.models import (
    KadiClinicalFactConfirmation,
    KadiClinicalReview,
    KadiClinicalReviewer,
    KadiClinicalStatement,
)


def category_label(category: str) -> str:
    try:
        return REVIEWER_CATEGORY_LABELS[ReviewerCategory(category)]
    except ValueError:
        return category


def coi_label(coi: Optional[str]) -> Optional[str]:
    if not coi:
        return None
    try:
        return COI_LABELS[ConflictOfInterest(coi)]
    except ValueError:
        return coi


def reviewer_label(reviewer: KadiClinicalReviewer) -> str:
    return verification_label(
        reviewer.verification_status, reviewer.verification_source, reviewer.verification_timestamp
    )


def reviewer_public(reviewer: KadiClinicalReviewer) -> Dict[str, Any]:
    return {
        "id": reviewer.id,
        "name": reviewer.name,
        "designation": reviewer.designation,
        "category": reviewer.category,
        "category_label": category_label(reviewer.category),
        "specialty": reviewer.specialty,
        "registration_number": reviewer.registration_number,
        "registration_authority": reviewer.registration_authority,
        "verification_status": reviewer.verification_status,
        "verification_label": reviewer_label(reviewer),
        "verification_source": reviewer.verification_source,
        "verification_timestamp": reviewer.verification_timestamp,
        "affiliation": reviewer.affiliation,
        "standing_disclosures": reviewer.standing_disclosures,
        "is_safety_board_member": reviewer.is_safety_board_member,
        "is_active": reviewer.is_active,
    }


def reviewer_snapshot(reviewer: KadiClinicalReviewer) -> Dict[str, Any]:
    """Frozen into a statement/decision at the moment the reviewer signs it."""
    snap = reviewer_public(reviewer)
    snap.pop("is_active", None)
    snap.pop("is_safety_board_member", None)
    snap["verification_timestamp"] = (
        reviewer.verification_timestamp.isoformat() if reviewer.verification_timestamp else None
    )
    snap["reviewer_id"] = snap.pop("id")
    return snap


def statement_view(stmt: KadiClinicalStatement, *, include_draft_fields: bool = False) -> Dict[str, Any]:
    view = {
        "statement_id": stmt.id,
        "review_id": stmt.review_id,
        "statement_version": stmt.statement_version,
        "supersedes_statement_id": stmt.supersedes_statement_id,
        "status": stmt.status,
        "provenance": ProvenanceClass.HUMAN_AUTHORED.value,
        "provenance_description": PROVENANCE_DESCRIPTIONS[ProvenanceClass.HUMAN_AUTHORED],
        "clinical_question": stmt.clinical_question,
        "evidence_reviewed": stmt.evidence_reviewed or [],
        "reviewer_statement": stmt.reviewer_statement,
        "limitations": stmt.limitations,
        "coi_category": stmt.coi_category,
        "coi_label": coi_label(stmt.coi_category),
        "coi_disclosure": stmt.coi_disclosure,
        "reviewer_snapshot": stmt.reviewer_snapshot,
        "reviewer_confirmation": stmt.confirmation_text is not None,
        "confirmation_text": stmt.confirmation_text,
        "confirmed_at": stmt.confirmed_at,
        "finalized_at": stmt.finalized_at.isoformat() if stmt.finalized_at else None,
        "content_sha256": stmt.content_sha256,
        "withdrawn_reason": stmt.withdrawn_reason,
        "withdrawn_at": stmt.withdrawn_at,
        "created_at": stmt.created_at,
        "updated_at": stmt.updated_at,
    }
    if not include_draft_fields and stmt.status not in PUBLISHED_STATEMENT_STATES:
        raise ValueError("Unpublished statements are not visible to this audience.")
    return view


def fact_view(fact: KadiClinicalFactConfirmation) -> Dict[str, Any]:
    decided = fact.decision != "PENDING"
    return {
        "fact_id": fact.id,
        "fact_key": fact.fact_key,
        "fact_question": fact.fact_question,
        "source": fact.source,
        "playbook_ref": fact.playbook_ref,
        "decision": fact.decision,
        "provenance": ProvenanceClass.HUMAN_REVIEWED.value if decided else None,
        "reviewer_note": fact.reviewer_note,
        "reviewer_snapshot": fact.reviewer_snapshot,
        "coi_category": fact.coi_category,
        "coi_label": coi_label(fact.coi_category),
        "coi_disclosure": fact.coi_disclosure,
        "decided_at": fact.decided_at,
    }


def review_summary(
    review: KadiClinicalReview,
    reviewer: Optional[KadiClinicalReviewer],
) -> Dict[str, Any]:
    return {
        "review_id": review.id,
        "case_id": review.case_id,
        "source_module": review.source_module,
        "review_type": review.review_type,
        "status": review.status,
        "clinical_question": review.clinical_question,
        "trigger": review.trigger,
        "trigger_ref": review.trigger_ref,
        "evidence_scope": review.evidence_scope,
        "insurer_name": review.insurer_name,
        "consent_confirmed_at": review.consent_confirmed_at,
        "assigned_reviewer": reviewer_public(reviewer) if reviewer else None,
        "assigned_at": review.assigned_at,
        "accepted_at": review.accepted_at,
        "coi_category": review.coi_category,
        "coi_label": coi_label(review.coi_category),
        "coi_disclosure": review.coi_disclosure,
        "decline_reason": review.decline_reason,
        "completed_at": review.completed_at,
        "cancelled_at": review.cancelled_at,
        "created_at": review.created_at,
    }


def case_holder_review_view(
    review: KadiClinicalReview,
    reviewer: Optional[KadiClinicalReviewer],
    statements: List[KadiClinicalStatement],
    facts: List[KadiClinicalFactConfirmation],
) -> Dict[str, Any]:
    published = [s for s in statements if s.status in PUBLISHED_STATEMENT_STATES]
    published.sort(key=lambda s: s.statement_version)
    current = next((s for s in reversed(published) if s.status == "FINALIZED"), None)
    view = review_summary(review, reviewer)
    view.update(
        {
            # What was shared with the reviewer — the case holder can always see it.
            "evidence_shared": [
                {k: item.get(k) for k in ("item_id", "kind", "label", "provenance", "source")}
                for item in (review.evidence_packet or [])
            ],
            "human_statement_exists": current is not None,
            "current_statement": statement_view(current) if current else None,
            "statement_history": [statement_view(s) for s in published],
            "draft_in_progress": any(s.status in ("DRAFT", "UNDER_REVIEW") for s in statements),
            "facts": [fact_view(f) for f in facts],
        }
    )
    return view


def annex_dict(stmt: KadiClinicalStatement) -> Dict[str, Any]:
    """Input for kadi.clinical_review.annex — the verbatim package rendering."""
    view = statement_view(stmt)
    return {
        **view,
        "finalized_at": view["finalized_at"],
    }
