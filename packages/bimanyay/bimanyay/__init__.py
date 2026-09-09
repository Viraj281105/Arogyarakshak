"""
BimaNyay — Post-Denial Insurance Dispute Resolution & IRDAI Appeals Engine.

Part of ArogyaRakshak.
"""

from bimanyay.models import (
    ClaimDenialInput,
    DisputeAuditResult,
    RegulatoryViolation,
    GrievanceTimelineEvent,
    GrievanceTrackerResponse,
)
from bimanyay.clause_auditor import audit_claim_denial
from bimanyay.drafter import (
    draft_gro_appeal_letter,
    draft_bimabharosa_summary,
    draft_ombudsman_statement,
)
from bimanyay.tracker import calculate_grievance_timeline


def analyze_insurance_denial(input_data: ClaimDenialInput) -> DisputeAuditResult:
    """
    End-to-end analysis of an insurance repudiation or deduction.
    Audits clauses against IRDAI regulations and drafts 3-tier appeals.
    """
    is_wrongful, prob, grounds, violations = audit_claim_denial(input_data)
    gro_letter = draft_gro_appeal_letter(input_data, grounds, violations)
    bimabharosa_text = draft_bimabharosa_summary(input_data, grounds)
    ombudsman_statement = draft_ombudsman_statement(input_data, grounds)

    return DisputeAuditResult(
        is_wrongful_denial=is_wrongful,
        reversal_probability_score=prob,
        primary_dispute_grounds=grounds,
        regulatory_violations=violations,
        level_1_gro_appeal=gro_letter,
        level_2_bimabharosa_text=bimabharosa_text,
        level_3_ombudsman_grounds=ombudsman_statement,
    )


__all__ = [
    "ClaimDenialInput",
    "DisputeAuditResult",
    "RegulatoryViolation",
    "GrievanceTimelineEvent",
    "GrievanceTrackerResponse",
    "audit_claim_denial",
    "draft_gro_appeal_letter",
    "draft_bimabharosa_summary",
    "draft_ombudsman_statement",
    "calculate_grievance_timeline",
    "analyze_insurance_denial",
]
