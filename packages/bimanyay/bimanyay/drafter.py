"""
BimaNyay Appeal & Grievance Package Drafter.

Generates structured, legally cited appeal documents across the 3 statutory tiers:
1. Insurer Grievance Redressal Officer (GRO)
2. IRDAI Bima Bharosa Portal (IGMS)
3. Council for Insurance Ombudsmen (CIO) Form VI
"""

from typing import List
from bimanyay.models import ClaimDenialInput, RegulatoryViolation


def draft_gro_appeal_letter(input_data: ClaimDenialInput, grounds: str, violations: List[RegulatoryViolation]) -> str:
    """Drafts formal representation letter addressed to the Insurer's Grievance Redressal Officer."""
    violations_text = "\n".join([f"- {v.clause_reference} ({v.statute_or_circular}): {v.violation_summary}" for v in violations])

    return f"""TO:
The Grievance Redressal Officer (GRO)
{input_data.insurer_name}

SUBJECT: Formal Appeal Against Wrongful Repudiation of Claim No. [CLAIM_NO] Under Policy No. {input_data.policy_number}

Dear Sir / Madam,

I am writing to register an urgent grievance against the arbitrary and wrongful repudiation / disallowance of my health insurance claim amounting to INR {input_data.denied_or_deducted_amount:,.2f} out of total claimed expenses of INR {input_data.claimed_amount:,.2f} for treatment of {input_data.diagnosis}.

REASON CITED BY INSURER:
"{input_data.denial_reason_raw}"

GROUNDS OF APPEAL:
{grounds}

STATUTORY IRDAI PROVISIONS VIOLATED:
{violations_text}

Under the IRDAI Master Circular on Health Insurance Business (May 29, 2024), health insurance claims cannot be repudiated without documented prior approval of the Claims Review Committee (CRC). Furthermore, insurers failing to settle claims within statutory timelines are liable to pay penal interest at Bank Rate + 2%.

I request you to re-examine my claim dossier and release the admissible settlement amount of INR {input_data.denied_or_deducted_amount:,.2f} within the statutory 15-day resolution window. Failing this, I will escalate this matter to the IRDAI Bima Bharosa portal and the Insurance Ombudsman.

Yours faithfully,
[POLICYHOLDER NAME]
Policy No: {input_data.policy_number}
"""


def draft_bimabharosa_summary(input_data: ClaimDenialInput, grounds: str) -> str:
    """Generates concise text strictly within the 2,000-character limit of the IRDAI Bima Bharosa web form."""
    summary = (
        f"Grievance against {input_data.insurer_name} for wrongful claim repudiation. "
        f"Policy No: {input_data.policy_number}. Disallowed Amount: INR {input_data.denied_or_deducted_amount:,.2f}. "
        f"Insurer Rejection Reason: '{input_data.denial_reason_raw}'. "
        f"Grounds: {grounds} "
        "Insurer failed to resolve dispute within 15-day statutory window under IRDAI Master Circular 2024. "
        "Requesting IRDAI regulatory intervention to direct settlement with statutory penal interest."
    )
    return summary[:2000]


def draft_ombudsman_statement(input_data: ClaimDenialInput, grounds: str) -> str:
    """Drafts Statement of Facts for Insurance Ombudsman Form VI under Rule 14(1)(b)."""
    return f"""STATEMENT OF FACTS FOR COMPLAINT TO INSURANCE OMBUDSMAN
(Under Rule 14(1)(b) of Insurance Ombudsman Rules, 2017)

1. Complainant Name & Details: [POLICYHOLDER NAME]
2. Insurer Name: {input_data.insurer_name}
3. Policy Number: {input_data.policy_number}
4. Policy Inception Date: Active continuously for {input_data.policy_age_years} years
5. Total Claim Amount: INR {input_data.claimed_amount:,.2f}
6. Disallowed / Repudiated Amount: INR {input_data.denied_or_deducted_amount:,.2f}
7. Nature of Disease / Treatment: {input_data.diagnosis}
8. Grounds for Relief:
{grounds}
9. Relief Sought:
Direction to {input_data.insurer_name} to pay INR {input_data.denied_or_deducted_amount:,.2f} along with 2% above bank rate penal interest for delayed settlement as mandated by IRDAI regulations.
"""
