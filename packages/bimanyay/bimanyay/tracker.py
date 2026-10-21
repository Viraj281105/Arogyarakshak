"""
BimaNyay Statutory SLA Grievance Timeline Tracker.

Computes milestones and statutory deadlines under:
1. IRDAI (Protection of Policyholders' Interests) Regulations - 15 days GRO SLA.
2. IRDAI Bima Bharosa portal escalation - 15 days regulatory review SLA.
3. Insurance Ombudsman Rules 2017 - 1 year (365 days) limitation period.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional

from kadi.explanation import (
    EvidenceItem,
    Explanation,
    ProvenanceClass,
    RuleUsed,
    TrustState,
    Undetermined,
    fact,
)

from bimanyay.models import GrievanceTimelineEvent, GrievanceTrackerResponse

# Citations exactly as recorded in this module (see the docstring above and the Tier 3
# instructions). The runtime does not re-verify them against the source texts.
_SRC_GRO = "IRDAI (Protection of Policyholders' Interests) Regulations — 15-day GRO SLA, as recorded in bimanyay/tracker.py"
_SRC_BIMA_BHAROSA = "IRDAI Bima Bharosa portal escalation — 15-day regulatory review SLA, as recorded in bimanyay/tracker.py"
_SRC_OMBUDSMAN = "Insurance Ombudsman Rules, 2017, rule 14(3)(b) (verified 2026-09-13 against the CIO consolidated text, per code comment)"

_TIER_RULES = {
    "LEVEL_1_GRO": ("Insurer GRO must resolve within 15 days", 15, _SRC_GRO),
    "LEVEL_2_BIMA_BHAROSA": ("Bima Bharosa review window of 15 days after the GRO window", 15, _SRC_BIMA_BHAROSA),
    "LEVEL_3_OMBUDSMAN": ("Ombudsman complaint limitation of one year (365 days)", 365, _SRC_OMBUDSMAN),
}


def _explain_deadline(
    tier: str,
    deadline: date,
    status: str,
    *,
    start_date: date,
    start_date_read: bool,
    current_tier: str,
    today: date,
) -> Explanation:
    name, days, source = _TIER_RULES[tier]
    after_gro = tier == "LEVEL_2_BIMA_BHAROSA"
    undetermined = [
        Undetermined(
            code="CLOCK_START_ASSUMED",
            reason=(
                "The deadline is counted from the dispute start date given to the app. When the insurer actually "
                "received or acknowledged the dispute is not recorded."
            ),
        ),
        Undetermined(
            code="CALENDAR_DAYS",
            reason="Days are counted as calendar days; holidays and working-day rules are not applied.",
        ),
    ]
    if not start_date_read:
        undetermined.insert(0, Undetermined(
            code="START_DATE_UNREADABLE",
            reason="The start date given could not be read, so today's date was used. Check every date below.",
        ))
    if after_gro:
        undetermined.append(Undetermined(
            code="ESCALATION_DATE_ASSUMED",
            reason=(
                "This window is placed immediately after the 15-day GRO window; the date the complaint was "
                "actually escalated is not recorded."
            ),
        ))
    if tier == "LEVEL_3_OMBUDSMAN":
        undetermined.append(Undetermined(
            code="REJECTION_DATE_NOT_USED",
            reason=(
                "The rule counts one year from the insurer's rejection or unsatisfactory reply; the system uses "
                "the dispute start date instead and does not know the rejection date."
            ),
        ))
    headline = f"This deadline is {deadline.isoformat()} — {days} days {'after the GRO deadline' if after_gro else 'after the dispute start date'}."
    return Explanation(
        finding_type="BIMANYAY_DEADLINE",
        headline=headline,
        evidence=[
            EvidenceItem(
                label="Dispute start date",
                value=start_date.isoformat() if start_date_read else None,
                provenance=ProvenanceClass.USER_ENTERED if start_date_read else ProvenanceClass.NOT_RECORDED,
            ),
            EvidenceItem(label="Current escalation stage", value=current_tier, provenance=ProvenanceClass.USER_ENTERED),
        ],
        rules=[
            RuleUsed(
                kind="STATUTORY_PERIOD",
                name=name,
                source=source,
                facts=[
                    fact("Period (calendar days)", days),
                    fact("Specific clause", "rule 14(3)(b)" if tier == "LEVEL_3_OMBUDSMAN" else None),
                ],
            ),
            RuleUsed(
                kind="COMPUTATION",
                name="Deadline = " + ("GRO deadline" if after_gro else "start date") + f" + {days} days; status from stage and today's date",
                facts=[
                    fact("Deadline", deadline.isoformat()),
                    fact("Status", status),
                    fact("Date treated as today (server date)", today.isoformat()),
                ],
            ),
        ],
        trust=TrustState(
            code="RULE_COMPUTED",
            label="Computed from the date you entered",
            detail="Exact arithmetic on your date; the period itself is as cited, not independently re-checked at runtime.",
        ),
        undetermined=undetermined,
    )


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
    start_date_read = True
    try:
        init_date = datetime.strptime(date_initiated, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        init_date = date.today()
        start_date_read = False

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

    def explain(tier: str, deadline: date) -> Explanation:
        return _explain_deadline(
            tier, deadline, determine_status(deadline, tier),
            start_date=init_date, start_date_read=start_date_read, current_tier=current_tier, today=today,
        )

    events: List[GrievanceTimelineEvent] = [
        GrievanceTimelineEvent(
            tier="LEVEL_1_GRO",
            title=f"Tier 1: Insurer GRO Representation ({insurer_name})",
            deadline_date=gro_deadline.isoformat(),
            status=determine_status(gro_deadline, "LEVEL_1_GRO"),
            explanation=explain("LEVEL_1_GRO", gro_deadline),
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
            explanation=explain("LEVEL_2_BIMA_BHAROSA", bima_deadline),
            instructions=(
                "If the insurer fails to resolve within 15 days or rejects the appeal, register an online "
                "complaint on the IRDAI Bima Bharosa portal (bimabharosa.irdai.gov.in) with the GRO token reference."
            )
        ),
        GrievanceTimelineEvent(
            tier="LEVEL_3_OMBUDSMAN",
            title="Tier 3: Insurance Ombudsman Complaint",
            deadline_date=ombudsman_deadline.isoformat(),
            status=determine_status(ombudsman_deadline, "LEVEL_3_OMBUDSMAN"),
            explanation=explain("LEVEL_3_OMBUDSMAN", ombudsman_deadline),
            # Rule citations verified 2026-09-13 against the CIO consolidated text
            # (cioins.co.in, "as amended till 09.11.2023") and G.S.R. 828(E).
            instructions=(
                "File a written or online complaint with the jurisdictional Insurance Ombudsman within one year "
                "of the insurer's rejection or unsatisfactory reply (Insurance Ombudsman Rules, 2017, rule 14(3)(b)). "
                "The award is binding on the insurer (rule 17(8)) and cannot exceed INR 50 lakh including relevant "
                "expenses (rule 17(3)(ii), as amended by G.S.R. 828(E) dated 09.11.2023)."
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
