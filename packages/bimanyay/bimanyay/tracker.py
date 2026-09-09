"""
BimaNyay Statutory SLA Grievance Timeline Tracker.

Computes milestones and statutory deadlines under:
1. IRDAI (Protection of Policyholders' Interests) Regulations - 15 days GRO SLA.
2. IRDAI Bima Bharosa portal escalation - 15 days regulatory review SLA.
3. Insurance Ombudsman Rules 2017 - 1 year (365 days) limitation period.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional
from bimanyay.models import GrievanceTimelineEvent, GrievanceTrackerResponse


def calculate_grievance_timeline(
    insurer_name: str,
    date_initiated: str,
    claim_number: Optional[str] = None,
    current_tier: str = "LEVEL_1_GRO"
) -> GrievanceTrackerResponse:
    """
    Computes statutory escalation deadlines starting from the date the dispute was first raised.

    Args:
        insurer_name: Name of insurance provider
        date_initiated: Date dispute was registered (ISO format YYYY-MM-DD)
        claim_number: Unique insurance claim identifier
        current_tier: Current escalation level ('LEVEL_1_GRO', 'LEVEL_2_BIMA_BHAROSA', 'LEVEL_3_OMBUDSMAN')

    Returns:
        GrievanceTrackerResponse containing milestone deadlines and actionable instructions.
    """
    try:
        init_date = datetime.strptime(date_initiated, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        init_date = date.today()

    today = date.today()

    # Deadlines
    gro_deadline = init_date + timedelta(days=15)
    bima_deadline = gro_deadline + timedelta(days=15)
    ombudsman_deadline = init_date + timedelta(days=365)

    def determine_status(deadline: date, tier_name: str) -> str:
        if current_tier == tier_name:
            return "OVERDUE" if today > deadline else "ACTIVE"
        if tier_name == "LEVEL_1_GRO" and current_tier in ("LEVEL_2_BIMA_BHAROSA", "LEVEL_3_OMBUDSMAN"):
            return "COMPLETED"
        if tier_name == "LEVEL_2_BIMA_BHAROSA" and current_tier == "LEVEL_3_OMBUDSMAN":
            return "COMPLETED"
        return "PENDING"

    events: List[GrievanceTimelineEvent] = [
        GrievanceTimelineEvent(
            tier="LEVEL_1_GRO",
            title=f"Tier 1: Insurer GRO Representation ({insurer_name})",
            deadline_date=gro_deadline.isoformat(),
            status=determine_status(gro_deadline, "LEVEL_1_GRO"),
            instructions=(
                "Submit the formal appeal to the Grievance Redressal Officer of the insurance company. "
                "By IRDAI mandate, the insurer must acknowledge within 3 working days and resolve within 15 days."
            )
        ),
        GrievanceTimelineEvent(
            tier="LEVEL_2_BIMA_BHAROSA",
            title="Tier 2: IRDAI Bima Bharosa Portal Escalation",
            deadline_date=bima_deadline.isoformat(),
            status=determine_status(bima_deadline, "LEVEL_2_BIMA_BHAROSA"),
            instructions=(
                "If the insurer fails to resolve within 15 days or rejects the appeal, register an online "
                "complaint on the IRDAI Bima Bharosa portal (bimabharosa.irdai.gov.in) with the GRO token reference."
            )
        ),
        GrievanceTimelineEvent(
            tier="LEVEL_3_OMBUDSMAN",
            title="Tier 3: Insurance Ombudsman Form VI Filing",
            deadline_date=ombudsman_deadline.isoformat(),
            status=determine_status(ombudsman_deadline, "LEVEL_3_OMBUDSMAN"),
            instructions=(
                "File Form VI with the jurisdictional Insurance Ombudsman within 1 year of claim repudiation. "
                "The Ombudsman offers binding arbitration with awards enforceable up to INR 50 Lakhs."
            )
        )
    ]

    return GrievanceTrackerResponse(
        claim_number=claim_number,
        insurer_name=insurer_name,
        date_initiated=init_date.isoformat(),
        current_tier=current_tier,
        gro_deadline_days=15,
        bimabharosa_deadline_days=15,
        ombudsman_limitation_days=365,
        timeline_events=events
    )
