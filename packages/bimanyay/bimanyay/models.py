"""
Pydantic Schemas for BimaNyay Insurance Denial and Grievance Engine.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ClaimDenialInput(BaseModel):
    """Input payload representing a denied or partially settled insurance claim."""
    policy_number: str = Field(..., description="Insurance policy number")
    insurer_name: str = Field(..., description="Name of insurance provider")
    policy_age_years: float = Field(..., description="Continuous renewal tenure in years")
    claimed_amount: float = Field(..., description="Total claimed hospital expenses")
    denied_or_deducted_amount: float = Field(..., description="Disallowed claim amount")
    denial_category: str = Field(
        ...,
        description="Category: 'PED_NON_DISCLOSURE', 'INVESTIGATION_ONLY', 'ROOM_RENT_CAPPING', 'EXCLUSION_CLAUSE', 'DELAYED_INTIMATION'"
    )
    denial_reason_raw: str = Field(..., description="Exact rejection reason quoted by insurer")
    diagnosis: str = Field(..., description="Primary clinical diagnosis")


class RegulatoryViolation(BaseModel):
    """Specific statutory clause violated by the insurer."""
    statute_or_circular: str
    clause_reference: str
    violation_summary: str
    legal_remedy: str


class DisputeAuditResult(BaseModel):
    """Outcome of legal and regulatory analysis on a claim denial."""
    is_wrongful_denial: bool
    reversal_probability_score: float = Field(..., ge=0.0, le=1.0)
    primary_dispute_grounds: str
    regulatory_violations: List[RegulatoryViolation] = []
    level_1_gro_appeal: str
    level_2_bimabharosa_text: str
    level_3_ombudsman_grounds: str


class GrievanceTimelineEvent(BaseModel):
    """Milestone in the statutory dispute escalation progression."""
    tier: str  # 'LEVEL_1_GRO', 'LEVEL_2_BIMA_BHAROSA', 'LEVEL_3_OMBUDSMAN'
    title: str
    deadline_date: str
    status: str  # 'PENDING', 'ACTIVE', 'OVERDUE', 'COMPLETED'
    instructions: str


class GrievanceTrackerResponse(BaseModel):
    """Calculated SLA timelines for escalating an unresolved insurance claim."""
    claim_number: Optional[str] = None
    insurer_name: str
    date_initiated: str
    current_tier: str
    gro_deadline_days: int = 15
    bimabharosa_deadline_days: int = 15
    ombudsman_limitation_days: int = 365
    timeline_events: List[GrievanceTimelineEvent] = []
