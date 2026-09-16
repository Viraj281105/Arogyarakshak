"""
BimaNyay Clause Auditor.

Audits insurance claim rejection reasons against statutory IRDAI mandates
and legal benchmarks.
"""

from typing import List, Tuple
from bimanyay.models import ClaimDenialInput, RegulatoryViolation


def audit_claim_denial(input_data: ClaimDenialInput) -> Tuple[bool, float, str, List[RegulatoryViolation]]:
    """
    Evaluates whether a claim repudiation or deduction violates IRDAI regulations.

    Returns:
        is_wrongful (bool): True if grounds for legal appeal exist.
        reversal_probability (float): Estimated likelihood of reversal (0.0 to 1.0).
        primary_grounds (str): Plain-language summary of dispute.
        violations (List[RegulatoryViolation]): Concrete citations of violated clauses.
    """
    violations: List[RegulatoryViolation] = []
    category = input_data.denial_category.upper()
    is_wrongful = False
    reversal_probability = 0.50
    primary_grounds = "The denial rationale was audited against general IRDAI fair practices guidelines."

    # 1. 5-Year Moratorium Rule (Regulation 16 / May 2024 Master Circular)
    if "PED" in category or "PRE_EXISTING" in category:
        if input_data.policy_age_years >= 5.0:
            is_wrongful = True
            reversal_probability = 0.95
            primary_grounds = (
                f"Policy has been continuously active for {input_data.policy_age_years} years. "
                "Under the IRDAI Master Circular on Health Insurance (May 29, 2024), the moratorium "
                "period is 5 years. Contesting this claim on grounds of non-disclosure is barred by law."
            )
            violations.append(
                RegulatoryViolation(
                    statute_or_circular="IRDAI Master Circular on Health Insurance Business (May 29, 2024)",
                    clause_reference="Clause 16 — Moratorium Period",
                    violation_summary="Insurer contested claim based on pre-existing condition after 5 continuous renewal years.",
                    legal_remedy="Invoke 5-year moratorium statutory bar and demand immediate claim settlement with 2% penal interest."
                )
            )
        else:
            is_wrongful = True
            reversal_probability = 0.70
            primary_grounds = (
                "Insurer must provide verifiable clinical documentary proof of pre-inception diagnosis. "
                "Oral declarations or doctor notes without diagnostic reports prior to inception are legally insufficient."
            )

    # 2. Investigation / Observation Only Denial
    elif "INVESTIGATION" in category:
        is_wrongful = True
        reversal_probability = 0.85
        primary_grounds = (
            f"The insurer rejected the claim for '{input_data.diagnosis}' claiming hospitalization was "
            "solely for diagnostic evaluation. However, active line of treatment and clinical stabilization "
            "warranted inpatient medical monitoring."
        )
        violations.append(
            RegulatoryViolation(
                statute_or_circular="IRDAI Health Insurance Operations & Claims Circular",
                clause_reference="Standard Health Definitions & Claims Settlement Guidelines",
                violation_summary="Arbitrary characterization of active clinical inpatient management as diagnostic investigation.",
                legal_remedy="Submit treating physician certification of medical necessity for continuous inpatient care."
            )
        )

    # 3. Room Rent Proportionate Deductions
    # No IRDAI provision backing this ground has been verified against a primary source.
    # Checked 2026-09-13: IRDAI/HLT/REG/CIR/194/07/2020 (22.07.2020, Consolidated Guidelines on
    # Product Filing), previously cited here, contains no proportionate-deduction clause, and
    # IRDAI/HLT/REG/CIR/193/07/2020 mentions proportionate deduction only in model policy wording
    # and a sample CIS. Both were superseded by Master Circular IRDAI/HLT/CIR/PRO/84/5/2024
    # (29.05.2024, Annexure-6). Do not re-add either as authority for this ground.
    elif "ROOM_RENT" in category:
        is_wrongful = True
        reversal_probability = 0.90
        primary_grounds = (
            "Insurer applied proportionate deductions across medical charges. The IRDAI provision said to "
            "limit proportionate deductions to room-linked charges (excluding ICU charges, medicines and "
            "implants) has NOT been verified against a primary source, so it must not be cited as settled law. "
            "Ask the insurer to identify the policy clause relied on and to show the deduction calculation."
        )
        violations.append(
            RegulatoryViolation(
                statute_or_circular="IRDAI provision not verified",
                clause_reference="UNVERIFIED — no primary-source citation",
                violation_summary="Proportionate deduction applied to non-room-rent items (ICU/implants/medicines).",
                legal_remedy="Request the insurer's itemised deduction calculation and the exact policy clause and IRDAI provision relied upon."
            )
        )

    # 4. Delayed Intimation / Submission
    elif "DELAY" in category:
        is_wrongful = True
        reversal_probability = 0.88
        primary_grounds = (
            "The insurer denied the claim citing delayed submission. Under Supreme Court rulings and "
            "IRDAI Circular Ref: IRDA/HLTH/MISC/CIR/216/09/2011, genuine claims cannot be rejected "
            "solely on technical grounds of delayed submission when valid reasons exist."
        )
        violations.append(
            RegulatoryViolation(
                statute_or_circular="IRDAI Circular Ref: IRDA/HLTH/MISC/CIR/216/09/2011",
                clause_reference="Claims settlement without mechanical delay rejections",
                violation_summary="Repudiation solely on timeline delay without examination of substantive medical merits.",
                legal_remedy="Submit affidavit of genuine circumstances causing submission delay and cite IRDAI circular."
            )
        )

    # 5. Generic Claims Review Committee Mandate
    if is_wrongful:
        violations.append(
            RegulatoryViolation(
                statute_or_circular="IRDAI Master Circular (May 29, 2024)",
                clause_reference="Claims Review Committee (CRC) Requirement",
                violation_summary="No claim can be repudiated without prior approval of the 3-member Claims Review Committee.",
                legal_remedy="Request proof of Claims Review Committee signed minutes authorizing the repudiation."
            )
        )

    return is_wrongful, reversal_probability, primary_grounds, violations
