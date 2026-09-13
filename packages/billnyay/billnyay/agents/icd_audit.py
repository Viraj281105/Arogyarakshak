"""
BillNyay — ICD-10 / Procedure Consistency Auditor (#64).

Flags hospital bills where the billed procedure looks clinically inconsistent with the
diagnosis's ICD-10 code — a common indicator of miscoding or upcoding worth a human
second look, not a fraud determination.

The ICD-10-to-expected-procedure table below is a small, curated subset covering common
inpatient scenarios, not the full ~70,000-code ICD-10-CM set. Absence of a code from
this table is reported honestly as "not checked", never as "consistent" or "fine" —
the same pattern DawaCheck's NPPA reference table and BillNyay's CGHS rate table use
for the same reason: a curated subset cannot license the same certainty
a complete reference would.
"""

import re
from typing import List, Optional

from pydantic import BaseModel, Field

# ICD-10 code prefix (letter + 2 digits, e.g. "K35") -> keywords a clinically
# consistent procedure should contain (case-insensitive substring match).
_ICD10_PROCEDURE_INDEX = {
    "K35": {
        "diagnosis_label": "Acute appendicitis",
        "expected_procedure_keywords": ["appendectomy"],
    },
    "K80": {
        "diagnosis_label": "Cholelithiasis (gallstones)",
        "expected_procedure_keywords": ["cholecystectomy"],
    },
    "I21": {
        "diagnosis_label": "Acute myocardial infarction",
        "expected_procedure_keywords": ["angioplasty", "bypass", "pci", "stent", "cabg"],
    },
    "S72": {
        "diagnosis_label": "Fracture of femur",
        "expected_procedure_keywords": ["fixation", "replacement", "arthroplasty", "orif"],
    },
    "N18": {
        "diagnosis_label": "Chronic kidney disease",
        "expected_procedure_keywords": ["dialysis", "transplant"],
    },
    "O82": {
        "diagnosis_label": "Delivery by caesarean section",
        "expected_procedure_keywords": ["caesarean", "cesarean", "c-section", "c section"],
    },
}

_ICD10_CODE_RE = re.compile(r"\b([A-TV-Z][0-9]{2})(?:\.[0-9A-Z]{1,4})?\b")


class ICDProcedureAuditItem(BaseModel):
    icd10_code: Optional[str] = None
    diagnosis_text: str
    procedures_billed: List[str]
    status: str = Field(
        ...,
        description=(
            '"consistent" (a billed procedure matches the code\'s expected keywords), '
            '"mismatched" (a code was found and referenced, and at least one procedure '
            "was billed, but none matches — worth a human review), "
            '"no_procedure_billed" (a code was found and referenced, but no procedure '
            'was billed at all — nothing to check consistency against), '
            '"code_not_found" (no ICD-10 code could be parsed from the diagnosis text), '
            'or "code_not_in_reference" (a code was found but this curated table does '
            "not cover it — NOT evidence of a mismatch)."
        ),
    )
    reference_entry_count: int


def _extract_icd10_code(diagnosis_text: str) -> Optional[str]:
    match = _ICD10_CODE_RE.search(diagnosis_text or "")
    return match.group(1).upper() if match else None


def audit_icd_procedure_consistency(
    diagnosis_text: str, procedures_billed: List[str]
) -> ICDProcedureAuditItem:
    """Checks whether any billed procedure is clinically consistent with the ICD-10
    code parsed from `diagnosis_text`, against the curated reference table above."""
    code = _extract_icd10_code(diagnosis_text)
    entry_count = len(_ICD10_PROCEDURE_INDEX)

    if code is None:
        return ICDProcedureAuditItem(
            icd10_code=None,
            diagnosis_text=diagnosis_text,
            procedures_billed=procedures_billed,
            status="code_not_found",
            reference_entry_count=entry_count,
        )

    reference = _ICD10_PROCEDURE_INDEX.get(code)
    if reference is None:
        return ICDProcedureAuditItem(
            icd10_code=code,
            diagnosis_text=diagnosis_text,
            procedures_billed=procedures_billed,
            status="code_not_in_reference",
            reference_entry_count=entry_count,
        )

    if not procedures_billed:
        return ICDProcedureAuditItem(
            icd10_code=code,
            diagnosis_text=diagnosis_text,
            procedures_billed=procedures_billed,
            status="no_procedure_billed",
            reference_entry_count=entry_count,
        )

    keywords = reference["expected_procedure_keywords"]
    procedures_lower = [p.lower() for p in procedures_billed]
    is_consistent = any(
        keyword in procedure for procedure in procedures_lower for keyword in keywords
    )

    return ICDProcedureAuditItem(
        icd10_code=code,
        diagnosis_text=diagnosis_text,
        procedures_billed=procedures_billed,
        status="consistent" if is_consistent else "mismatched",
        reference_entry_count=entry_count,
    )
