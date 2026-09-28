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

import re
from typing import Any, Dict, List, Literal, Optional, Sequence

from pydantic import BaseModel, Field

from .agents.icd_audit import (
    ICD_REFERENCE_SOURCE,
    audit_icd_procedure_consistency,
    extract_icd10_code,
    get_reference_entry,
    reference_codes,
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
    # EVALUATED, or UNAVAILABLE when the safety rules could not be evaluated.
    safety_check_status: Literal["EVALUATED", "UNAVAILABLE"] = "EVALUATED"
    provenance: Literal["AI_DERIVED"] = "AI_DERIVED"
    method: str = "Rule-based ICD-10 code to procedure-keyword match (machine-derived, no LLM)"
    # Bill lines set aside as non-interventions (room, nursing, consultation, ...).
    excluded_administrative_items: List[str] = Field(default_factory=list)
    # Billed interventions the curated reference associates with a diagnosis that is NOT
    # documented here (assessed, and in conflict — never listed as "not assessed").
    conflicting_items: List[str] = Field(default_factory=list)
    # Billed interventions the curated reference does not cover — NOT assessed.
    not_assessed_items: List[str] = Field(default_factory=list)
    # FULL: every clinical item was checked; PARTIAL: some were not; NONE: nothing was.
    coverage: Literal["FULL", "PARTIAL", "NONE"] = "NONE"


_ADMINISTRATIVE_CHARGE = re.compile(
    r"\b(?:room|bed|ward|nursing|consultation|visit|admission|registration|diet|food|meal|"
    r"pharmacy|consumables?|attendant|ambulance|misc(?:ellaneous)?|laundry|linen|stay|rent|icu|"
    r"service\s+charges?|documentation|administrative|admin|processing|medical\s+records?|"
    r"records?\s+fee|certificate|file\s+charges?|gst|tax(?:es)?|discount|deposit|advance|"
    r"housekeeping|canteen|parking|telephone|operation\s+theat(?:re|er)\s+charges?|ot\s+charges?)\b",
    re.IGNORECASE,
)


def is_administrative_charge(line: str) -> bool:
    return bool(_ADMINISTRATIVE_CHARGE.search(line or ""))


def _expected_for(procedure: str, codes) -> bool:
    text = (procedure or "").lower()
    for code in codes:
        entry = get_reference_entry(code)
        if entry and any(k in text for k in entry["expected_procedure_keywords"]):
            return True
    return False


def _expected_for_other_diagnoses(procedure: str, documented_codes) -> bool:
    """True when the curated table lists this intervention for some diagnosis code that is
    NOT among the documented ones."""
    text = (procedure or "").lower()
    for code in reference_codes():
        if code in documented_codes:
            continue
        entry = get_reference_entry(code)
        if entry and any(k in text for k in entry["expected_procedure_keywords"]):
            return True
    return False


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
    safety_check_available: bool = True,
) -> PlausibilityAssessment:
    evidence = list(diagnoses) + list(procedures)
    # Bill lines extracted as "procedures" include room, nursing, consultation, etc. Those
    # are not interventions and must never be read as inconsistent with a diagnosis.
    administrative = [p.value for p in procedures if p.value and is_administrative_charge(p.value)]
    procedure_names = [p.value for p in procedures if p.value and not is_administrative_charge(p.value)]

    if not diagnoses and not procedure_names:
        early_reasons = (
            [] if safety_check_available
            else ["The clinical safety check could not be run for this case (safety check unavailable)."]
        )
        return PlausibilityAssessment(
            status="INSUFFICIENT_INFORMATION",
            summary=(
                "Insufficient evidence for assessment: no diagnosis or clinical procedure was found "
                "in the supplied documents. Upload the discharge summary or clinical notes."
            ),
            clinical_review_required=bool(early_reasons),
            review_reasons=early_reasons,
            evidence_used=[],
            excluded_administrative_items=administrative,
            coverage="NONE",
            safety_check_status="EVALUATED" if safety_check_available else "UNAVAILABLE",
        )

    results = [audit_icd_procedure_consistency(d.value, procedure_names) for d in diagnoses]
    statuses = {r.status for r in results}
    # A billed intervention the curated table expects for a DIFFERENT diagnosis that is not
    # documented here is a conflict, not an unassessed extra: "appendectomy + cholecystectomy"
    # with only appendicitis documented must not read as plausible.
    documented_codes = {r.icd10_code for r in results if r.icd10_code}
    conflicting = [
        p for p in procedure_names
        if _expected_for_other_diagnoses(p, documented_codes) and not _expected_for(p, documented_codes)
    ]
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
    elif "consistent" in statuses and conflicting:
        status = "CLINICAL_REVIEW_RECOMMENDED"
        matched = [p for p in procedure_names if p not in conflicting and _expected_for(p, documented_codes)]
        summary = (
            f"Some documented interventions ({', '.join(matched) or 'none'}) appear broadly consistent with "
            f"the documented diagnosis, but others ({', '.join(conflicting)}) are ones the curated reference "
            "associates with a different diagnosis that is not documented here. The result is mixed, so it is "
            "not reported as plausible. This may reflect a missing diagnosis in the documents or a coding "
            "error; it is not evidence of wrongdoing and not a necessity determination."
        )
        reasons.append("Mixed result: an intervention matches a diagnosis that is not documented (ambiguity).")
    elif "consistent" in statuses:
        ref = references[0] if references else None
        label = f"{ref.icd10_code} — {ref.diagnosis_label}" if ref else "the documented diagnosis"
        keywords = [k for r in references for k in r.expected_procedure_keywords]
        matched = [p for p in procedure_names if any(k in p.lower() for k in keywords)]
        not_assessed = [p for p in procedure_names if p not in matched]
        status = "PLAUSIBLE"
        summary = (
            f"Based on the supplied documentation, the documented intervention ({', '.join(matched)}) "
            f"appears broadly consistent with the documented diagnosis ({label}) according to "
            "the curated reference named below."
        )
        if not_assessed:
            summary += (
                f" Other billed item(s) ({', '.join(not_assessed)}) are outside that reference and "
                "were NOT assessed — this check does not say they were appropriate."
            )
        unassessed_dx = [d.value for d, r in zip(diagnoses, results) if r.status in ("code_not_found", "code_not_in_reference")]
        if unassessed_dx:
            summary += (
                f" Diagnosis(es) {', '.join(unassessed_dx)} could not be assessed by the reference and are "
                "NOT treated as compatible."
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
            detail = "no clinical procedure was found to compare against the diagnosis"
            if administrative:
                detail += " (only administrative charges such as room or nursing were billed)"
        elif "code_not_in_reference" in statuses:
            detail = "the diagnosis code is not covered by the curated reference (not evidence of a mismatch)"
        else:
            detail = "no ICD-10 code could be read from the documented diagnosis"
        summary = f"Insufficient evidence for assessment: {detail}."
        reasons.append("Evidence is incomplete for an automated check.")

    if not safety_check_available:
        # Unknown is not safe: a failed safety check can never read like "nothing fired".
        reasons.append("The clinical safety check could not be run for this case (safety check unavailable).")
    if safety_escalations > 0:
        reasons.append("An active clinical safety rule fired for this case (high-risk signal).")
        if status in ("PLAUSIBLE", "INSUFFICIENT_INFORMATION"):
            status = "CLINICAL_REVIEW_RECOMMENDED"

    not_assessed_items: List[str] = []
    if status == "PLAUSIBLE" or (status == "CLINICAL_REVIEW_RECOMMENDED" and "consistent" in statuses):
        keywords = [k for r in references for k in r.expected_procedure_keywords]
        not_assessed_items = [
            p for p in procedure_names if not any(k in p.lower() for k in keywords) and p not in conflicting
        ]
    if statuses & {"consistent", "mismatched"}:
        # A diagnosis the reference could not read or does not cover was not assessed
        # either; "FULL" coverage must never hide it behind another diagnosis's result.
        not_assessed_items += [
            f"{d.value} (diagnosis not covered by the reference)"
            for d, r in zip(diagnoses, results)
            if r.status in ("code_not_found", "code_not_in_reference")
        ]
    coverage = "PARTIAL" if not_assessed_items else ("NONE" if status == "INSUFFICIENT_INFORMATION" else "FULL")

    return PlausibilityAssessment(
        safety_check_status="EVALUATED" if safety_check_available else "UNAVAILABLE",
        excluded_administrative_items=administrative,
        conflicting_items=conflicting,
        not_assessed_items=not_assessed_items,
        coverage=coverage,
        status=status,
        summary=summary,
        clinical_review_required=bool(reasons),
        review_reasons=reasons,
        evidence_used=evidence,
        references=references,
        guideline_citations=citations,
        guideline_note=NO_GUIDELINE_NOTE if not citations else "Citations are from registered guideline records.",
    )
