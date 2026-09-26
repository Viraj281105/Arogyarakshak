"""
BillNyay — Clinical Plausibility Review (ADR-011).

Bounded internal decision support. Answers one narrow question: do the SUPPLIED
documents show a clinically plausible relationship between the documented diagnosis and
the documented procedure? It never determines medical necessity, never predicts an
insurer outcome, and never cites a guideline that is not actually registered here.

Method: the curated ICD-10 to expected-procedure table in `agents.icd_audit`. Anything
that table cannot decide is reported as INSUFFICIENT_INFORMATION and routed toward a
human reviewer, not guessed.
"""

from typing import Any, Dict, List, Literal, Optional, Sequence

from pydantic import BaseModel, Field

from .agents.icd_audit import (
    ICD_REFERENCE_SOURCE,
    audit_icd_procedure_consistency,
    extract_icd10_code,
    get_reference_entry,
)

PlausibilityStatus = Literal[
    "PLAUSIBLE",
    "INSUFFICIENT_INFORMATION",
    "POTENTIAL_INCONSISTENCY",
    "CLINICAL_REVIEW_RECOMMENDED",
]

PLAUSIBILITY_DISCLAIMER = (
    "This is a limited plausibility assessment and is not a clinical necessity "
    "determination. It does not predict any insurer decision."
)

NO_GUIDELINE_NOTE = (
    "No validated clinical guideline is registered in this build, so none is cited. "
    "The only reference used is the project-curated code table named above."
)


class EvidenceRef(BaseModel):
    item_id: Optional[str] = None
    kind: str
    value: str
    provenance: str = "AI_DERIVED"


class ReferenceUsed(BaseModel):
    name: str
    type: str
    version: str
    note: str
    icd10_code: str
    diagnosis_label: str
    expected_procedure_keywords: List[str]


class GuidelineCitation(BaseModel):
    """Only ever built from a registered guideline record — never from model output."""

    title: str
    issuer: str
    version: str
    section: str
    applies_to_icd10: str


class PlausibilityAssessment(BaseModel):
    status: PlausibilityStatus
    summary: str
    disclaimer: str = PLAUSIBILITY_DISCLAIMER
    is_necessity_determination: Literal[False] = False
    clinical_review_required: bool
    review_reasons: List[str] = Field(default_factory=list)
    evidence_used: List[EvidenceRef] = Field(default_factory=list)
    references: List[ReferenceUsed] = Field(default_factory=list)
    guideline_citations: List[GuidelineCitation] = Field(default_factory=list)
    guideline_note: str = NO_GUIDELINE_NOTE
    provenance: Literal["AI_DERIVED"] = "AI_DERIVED"
    method: str = "Rule-based ICD-10 code to procedure-keyword match (machine-derived, no LLM)"


def _registered_citations(
    codes: Sequence[str], registry: Optional[Sequence[Dict[str, Any]]]
) -> List[GuidelineCitation]:
    """Citations come only from a supplied registry of validated guideline records that
    carry title, issuer, version and section. Incomplete records are dropped, not
    completed."""
    if not registry:
        return []
    citations: List[GuidelineCitation] = []
    for record in registry:
        if record.get("applies_to_icd10") not in codes:
            continue
        try:
            citations.append(GuidelineCitation(**{k: record[k] for k in GuidelineCitation.model_fields}))
        except (KeyError, TypeError, ValueError):
            continue
    return citations


def assess_clinical_plausibility(
    diagnoses: Sequence[EvidenceRef],
    procedures: Sequence[EvidenceRef],
    *,
    safety_escalations: int = 0,
    guideline_registry: Optional[Sequence[Dict[str, Any]]] = None,
) -> PlausibilityAssessment:
    evidence = list(diagnoses) + list(procedures)
    procedure_names = [p.value for p in procedures if p.value]

    if not diagnoses and not procedures:
        return PlausibilityAssessment(
            status="INSUFFICIENT_INFORMATION",
            summary=(
                "Insufficient evidence for assessment: no diagnosis or procedure was found in "
                "the supplied documents. Upload the discharge summary or clinical notes."
            ),
            clinical_review_required=False,
            review_reasons=[],
            evidence_used=[],
        )

    results = [audit_icd_procedure_consistency(d.value, procedure_names) for d in diagnoses]
    statuses = {r.status for r in results}
    references: List[ReferenceUsed] = []
    for r in results:
        if r.icd10_code:
            entry = get_reference_entry(r.icd10_code)
            if entry:
                references.append(
                    ReferenceUsed(
                        name=ICD_REFERENCE_SOURCE["name"],
                        type=ICD_REFERENCE_SOURCE["type"],
                        version=ICD_REFERENCE_SOURCE["version"],
                        note=ICD_REFERENCE_SOURCE["note"],
                        icd10_code=r.icd10_code,
                        diagnosis_label=entry["diagnosis_label"],
                        expected_procedure_keywords=list(entry["expected_procedure_keywords"]),
                    )
                )

    codes = [c for c in (extract_icd10_code(d.value) for d in diagnoses) if c]
    citations = _registered_citations(codes, guideline_registry)
    reasons: List[str] = []
    proc_text = ", ".join(procedure_names) or "none documented"

    if "consistent" in statuses and "mismatched" in statuses:
        status: PlausibilityStatus = "CLINICAL_REVIEW_RECOMMENDED"
        summary = (
            "The documents contain more than one diagnosis and the automated check gives "
            "conflicting results across them. A clinician should look at how the documented "
            f"procedures ({proc_text}) relate to each diagnosis."
        )
        reasons.append("Conflicting automated results across diagnoses (ambiguity).")
    elif "consistent" in statuses:
        ref = references[0] if references else None
        label = f"{ref.icd10_code} — {ref.diagnosis_label}" if ref else "the documented diagnosis"
        status = "PLAUSIBLE"
        summary = (
            f"Based on the supplied documentation, the documented intervention ({proc_text}) "
            f"appears broadly consistent with the documented diagnosis ({label}) according to "
            "the curated reference named below."
        )
    elif "mismatched" in statuses:
        ref = next((x for x in references), None)
        label = f"{ref.icd10_code} ({ref.diagnosis_label})" if ref else "the documented diagnosis"
        status = "POTENTIAL_INCONSISTENCY"
        summary = (
            f"The documented intervention(s) ({proc_text}) do not match the procedures the "
            f"curated reference lists for {label}. This may reflect a coding error, an "
            "additional indication not captured in the documents, or a documentation gap. "
            "It is not evidence of wrongdoing and not a necessity determination."
        )
        reasons.append("Documented diagnosis and documented intervention appear inconsistent.")
    else:
        status = "INSUFFICIENT_INFORMATION"
        if not diagnoses:
            detail = "no diagnosis was found in the supplied documents"
        elif statuses == {"no_procedure_billed"}:
            detail = "no procedure was found to compare against the diagnosis"
        elif "code_not_in_reference" in statuses:
            detail = "the diagnosis code is not covered by the curated reference (not evidence of a mismatch)"
        else:
            detail = "no ICD-10 code could be read from the documented diagnosis"
        summary = f"Insufficient evidence for assessment: {detail}."
        reasons.append("Evidence is incomplete for an automated check.")

    if safety_escalations > 0:
        reasons.append("An active clinical safety rule fired for this case (high-risk signal).")
        if status in ("PLAUSIBLE", "INSUFFICIENT_INFORMATION"):
            status = "CLINICAL_REVIEW_RECOMMENDED"

    return PlausibilityAssessment(
        status=status,
        summary=summary,
        clinical_review_required=bool(reasons),
        review_reasons=reasons,
        evidence_used=evidence,
        references=references,
        guideline_citations=citations,
        guideline_note=NO_GUIDELINE_NOTE if not citations else "Citations are from registered guideline records.",
    )
