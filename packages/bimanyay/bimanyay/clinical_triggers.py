"""
BimaNyay — when does a denial turn on clinical interpretation? (ADR-011)

Some repudiations are administrative (late intimation, room-rent caps): the statute and
the policy wording decide them. Others hinge on a clinical judgment — "admitted for
investigation only", "condition was pre-existing", "not medically necessary". For those,
an appeal is stronger with an attributable statement from a named clinician, and
ArogyaRakshak must not manufacture one. This module only identifies the second kind and
suggests a neutral question; it never predicts how an insurer will decide.
"""

import re
from typing import List, Optional

from pydantic import BaseModel, Field

CLINICAL_DENIAL_CATEGORIES = {
    "INVESTIGATION_ONLY": (
        "The insurer characterised the admission as for investigation only — whether active "
        "treatment required inpatient care is a clinical question."
    ),
    "PED_NON_DISCLOSURE": (
        "The insurer alleges a pre-existing disease — whether the condition existed before "
        "the policy, and when it was diagnosable, is a clinical question."
    ),
}

ADMINISTRATIVE_DENIAL_CATEGORIES = frozenset(
    {"ROOM_RENT_CAPPING", "DELAYED_INTIMATION", "EXCLUSION_CLAUSE"}
)

_CLINICAL_REASON_PATTERNS = [
    (re.compile(r"\bmedical(?:ly)?\s+(?:un)?necess", re.I), "the reason disputes medical necessity"),
    (re.compile(r"\bnot\s+(?:clinically\s+)?(?:justified|indicated|required)\b", re.I), "the reason says treatment was not indicated"),
    (re.compile(r"\b(?:opd|out[- ]?patient|day[- ]?care)\s+basis\b|\bcould\s+have\s+been\s+(?:managed|treated)\b", re.I), "the reason says the condition could have been managed without admission"),
    (re.compile(r"\bpre[- ]?existing\b|\bped\b", re.I), "the reason alleges a pre-existing condition"),
    (re.compile(r"\bexperimental\b|\bunproven\b", re.I), "the reason calls the treatment experimental or unproven"),
    (re.compile(r"\binvestigation\s+only\b|\bdiagnostic\s+admission\b", re.I), "the reason calls the admission diagnostic only"),
]


class ClinicalReviewTrigger(BaseModel):
    requires_clinical_interpretation: bool
    reasons: List[str] = Field(default_factory=list)
    suggested_clinical_question: Optional[str] = None
    note: str = (
        "Identifies whether the denial reason turns on clinical judgment. It does not predict "
        "the insurer's decision, and ArogyaRakshak does not write the clinical opinion itself — "
        "a named clinician must."
    )


def assess_clinical_review_need(denial_category: str, denial_reason_raw: str, diagnosis: str) -> ClinicalReviewTrigger:
    reasons: List[str] = []
    category = (denial_category or "").strip().upper()
    if category in CLINICAL_DENIAL_CATEGORIES:
        reasons.append(CLINICAL_DENIAL_CATEGORIES[category])
    for pattern, reason in _CLINICAL_REASON_PATTERNS:
        if pattern.search(denial_reason_raw or "") and reason not in reasons:
            reasons.append(reason)

    if not reasons:
        return ClinicalReviewTrigger(requires_clinical_interpretation=False)

    dx = (diagnosis or "the documented condition").strip()[:200]
    return ClinicalReviewTrigger(
        requires_clinical_interpretation=True,
        reasons=reasons,
        suggested_clinical_question=(
            f"Based on the records you review, what is your professional opinion on the "
            f"insurer's stated reason for denying the claim for {dx}? Please state what the "
            "records do and do not show, and the limits of your review."
        ),
    )
