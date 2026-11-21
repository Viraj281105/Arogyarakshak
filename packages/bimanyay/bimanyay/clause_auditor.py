"""
BimaNyay Clause Auditor.

Audits insurance claim rejection reasons against statutory IRDAI mandates
and legal benchmarks.
"""

from typing import List, Tuple

from bimanyay import catalogue
from bimanyay.models import ClaimDenialInput, RegulatoryViolation


def audit_claim_denial(
    input_data: ClaimDenialInput, language: str = "en"
) -> Tuple[bool, float, str, List[RegulatoryViolation]]:
    """
    Evaluates whether a claim repudiation or deduction violates IRDAI regulations.

    ``language`` ("en", "hi", "mr"; anything else is English) only selects the wording of the
    grounds and the violation text, read from ``bimanyay.catalogue``. The decision and the
    reversal prior never depend on it. Hindi/Marathi wording is NEEDS NATIVE-SPEAKER QA.

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
    primary_grounds = catalogue.grounds("default", language)

    def cite(key: str) -> None:
        violations.append(RegulatoryViolation(**catalogue.violation(key, language)))

    # 1. 5-Year Moratorium Rule (Regulation 16 / May 2024 Master Circular)
    if "PED" in category or "PRE_EXISTING" in category:
        if input_data.policy_age_years >= 5.0:
            is_wrongful = True
            reversal_probability = 0.95
            primary_grounds = catalogue.grounds(
                "ped_moratorium", language, policy_age_years=input_data.policy_age_years
            )
            cite("moratorium")
        else:
            is_wrongful = True
            reversal_probability = 0.70
            primary_grounds = catalogue.grounds("ped_documentary", language)

    # 2. Investigation / Observation Only Denial
    elif "INVESTIGATION" in category:
        is_wrongful = True
        reversal_probability = 0.85
        primary_grounds = catalogue.grounds("investigation", language, diagnosis=input_data.diagnosis)
        cite("investigation")

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
        primary_grounds = catalogue.grounds("room_rent", language)
        cite("room_rent")

    # 4. Delayed Intimation / Submission
    elif "DELAY" in category:
        is_wrongful = True
        reversal_probability = 0.88
        primary_grounds = catalogue.grounds("delay", language)
        cite("delay")

    # 5. Generic Claims Review Committee Mandate
    if is_wrongful:
        cite("crc")

    return is_wrongful, reversal_probability, primary_grounds, violations
