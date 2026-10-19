"""
DaaviSetu — Pre-Authorization Readiness Assistant (ADR-011).

A completeness checker, not an approval engine. It answers: which documents that are
commonly requested for this kind of pre-authorization can be found in the case, and
which clinical facts still need a clinician to confirm them?

Rules that keep it honest:
- A checklist item names a KIND of documentation ("Previous treatment history"). It never
  asserts a fact about the claimant. Playbook labels phrased as assertions are rejected.
- Presence is decided only from the case's own evidence (extracted entities, or a keyword
  found in the redacted document text — reported as the weaker kind of evidence it is).
- A clinical fact is never marked satisfied by software. It stays NEEDS_CLINICAL_CONFIRMATION
  until a named reviewer confirms it, and a rejection is shown as a rejection.
- Nothing here predicts, estimates or claims to improve approval.
"""

import re
from typing import Dict, List, Literal, Optional, Sequence

from pydantic import BaseModel, Field, field_validator

from kadi.explanation import (
    EvidenceItem,
    Explanation,
    ProvenanceClass,
    RuleUsed,
    TrustState,
    Undetermined,
    fact,
)

EvidenceKind = Literal["entity", "document_keywords", "case_total"]
ItemStatus = Literal[
    "PRESENT",
    "MISSING",
    "NEEDS_CLINICAL_CONFIRMATION",
    "CONFIRMED_BY_REVIEWER",
    "REJECTED_BY_REVIEWER",
    "REVIEWER_COULD_NOT_DETERMINE",
]

READINESS_DISCLAIMER = (
    "This checklist lists documentation commonly requested for a cashless "
    "pre-authorization. It does not predict, estimate or influence the insurer's decision, "
    "and ArogyaRakshak has not verified what the documents say."
)

BASELINE_SOURCE = (
    "DaaviSetu generic baseline: the kinds of information the standard cashless "
    "pre-authorization request asks the hospital to provide (presenting complaints and "
    "clinical findings, provisional diagnosis, proposed treatment, past history, cost "
    "estimate). Not insurer-specific."
)

MAX_ITEMS = 40
_ITEM_ID = re.compile(r"^[a-z0-9][a-z0-9_\-]{1,48}$")
# Labels must describe documentation, not assert something about the claimant.
_ASSERTION = re.compile(
    r"\b(?:patient|claimant|insured|member|he|she)\s+(?:had|has|have|was|were|is|underwent|failed|received|took)\b",
    re.IGNORECASE,
)
_ENTITY_TYPES = frozenset({"diagnosis", "procedure", "hospital", "medicine", "billing_item"})


class EvidenceRule(BaseModel):
    kind: EvidenceKind
    entity_type: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)

    @field_validator("keywords")
    @classmethod
    def _keywords(cls, v: List[str]) -> List[str]:
        cleaned = [" ".join(k.split()).strip() for k in v if isinstance(k, str)]
        if any(not (2 <= len(k) <= 40) for k in cleaned):
            raise ValueError("Each keyword must be 2-40 characters.")
        if len(cleaned) > 20:
            raise ValueError("At most 20 keywords per item.")
        return cleaned

    def check(self) -> "EvidenceRule":
        if self.kind == "entity" and self.entity_type not in _ENTITY_TYPES:
            raise ValueError(f"entity_type must be one of {sorted(_ENTITY_TYPES)}.")
        if self.kind == "document_keywords" and not self.keywords:
            raise ValueError("document_keywords rules need at least one keyword.")
        return self


class ChecklistItem(BaseModel):
    item_id: str
    label: str = Field(..., max_length=120)
    evidence_rule: EvidenceRule
    clinical_fact: bool = False
    # Neutral question put to a clinician when the item is a clinical fact.
    clinical_fact_question: Optional[str] = Field(None, max_length=400)
    note: Optional[str] = Field(None, max_length=300)

    @field_validator("item_id")
    @classmethod
    def _item_id(cls, v: str) -> str:
        if not _ITEM_ID.match(v):
            raise ValueError("item_id must be a lowercase slug (a-z, 0-9, _ or -).")
        return v

    @field_validator("label", "clinical_fact_question", "note")
    @classmethod
    def _no_claimant_assertions(cls, v: Optional[str]) -> Optional[str]:
        if v and _ASSERTION.search(v):
            raise ValueError(
                "Checklist text must describe documentation, not assert a fact about the "
                "claimant (e.g. use 'Previous treatment history', not 'Patient had failed "
                "conservative treatment')."
            )
        return v


def validate_items(items: Sequence[ChecklistItem]) -> List[ChecklistItem]:
    if len(items) > MAX_ITEMS:
        raise ValueError(f"A checklist may contain at most {MAX_ITEMS} items.")
    seen = set()
    for item in items:
        item.evidence_rule.check()
        if item.item_id in seen:
            raise ValueError(f"Duplicate item_id '{item.item_id}'.")
        seen.add(item.item_id)
        if item.clinical_fact and not item.clinical_fact_question:
            raise ValueError(f"Clinical-fact item '{item.item_id}' needs a clinical_fact_question.")
    return list(items)


BASELINE_ITEMS: List[ChecklistItem] = validate_items(
    [
        ChecklistItem(
            item_id="diagnosis_documented",
            label="Provisional diagnosis documented",
            evidence_rule=EvidenceRule(kind="entity", entity_type="diagnosis"),
        ),
        ChecklistItem(
            item_id="procedure_documented",
            label="Proposed procedure or line of treatment documented",
            evidence_rule=EvidenceRule(kind="entity", entity_type="procedure"),
        ),
        ChecklistItem(
            item_id="hospital_identified",
            label="Treating hospital identified",
            evidence_rule=EvidenceRule(kind="entity", entity_type="hospital"),
        ),
        ChecklistItem(
            item_id="cost_estimate_available",
            label="Estimated cost of treatment available",
            evidence_rule=EvidenceRule(kind="case_total"),
        ),
        ChecklistItem(
            item_id="investigation_reports",
            label="Investigation report(s) supporting the diagnosis",
            evidence_rule=EvidenceRule(
                kind="document_keywords",
                keywords=["investigation", "report", "x-ray", "xray", "mri", "ct scan",
                          "ultrasound", "usg", "blood test", "cbc", "biopsy", "ecg"],
            ),
        ),
        ChecklistItem(
            item_id="clinical_findings",
            label="Presenting complaints and clinical findings",
            evidence_rule=EvidenceRule(
                kind="document_keywords",
                keywords=["chief complaint", "presenting complaint", "complaints of",
                          "clinical findings", "on examination", "o/e", "history of present illness"],
            ),
        ),
        ChecklistItem(
            item_id="previous_treatment_history",
            label="Previous treatment history for this condition",
            evidence_rule=EvidenceRule(
                kind="document_keywords",
                keywords=["previous treatment", "past treatment", "conservative",
                          "treated with", "medication history", "past history"],
            ),
            clinical_fact=True,
            clinical_fact_question=(
                "Do the case records document the treatment tried before the proposed "
                "procedure? Confirm only what the records you reviewed actually show."
            ),
        ),
    ]
)


class CaseEvidence(BaseModel):
    """What the case actually contains. Built by the API from Kadi entities."""

    # type -> [{id, value, source_file?}]; source_file only when the entity recorded one.
    entities: Dict[str, List[Dict[str, str]]] = Field(default_factory=dict)
    document_text: str = ""
    case_total: float = 0.0


class FactDecisionRef(BaseModel):
    decision: Literal["PENDING", "CONFIRMED", "REJECTED", "CANNOT_DETERMINE"]
    fact_id: str
    reviewer_name: Optional[str] = None
    reviewer_verification_label: Optional[str] = None
    coi_label: Optional[str] = None
    decided_at: Optional[str] = None


class ItemEvidence(BaseModel):
    kind: str
    reference: str
    provenance: str


class ReadinessItemResult(BaseModel):
    item_id: str
    label: str
    status: ItemStatus
    evidence_strength: Optional[Literal["EXTRACTED_ENTITY", "KEYWORD_MATCH", "CASE_TOTAL", "REVIEWER_DECISION"]] = None
    evidence: List[ItemEvidence] = Field(default_factory=list)
    clinical_fact: bool = False
    clinical_fact_question: Optional[str] = None
    clinical_decision: Optional[FactDecisionRef] = None
    origin: Literal["BASELINE", "INSTITUTION_PLAYBOOK"] = "BASELINE"
    note: Optional[str] = None
    # "Why am I seeing this?" trail (ADR-015). Additive.
    explanation: Optional[Explanation] = None


EVIDENCE_SCOPE_NOTE = (
    "Searched: the extracted diagnoses, procedures, hospital and costs, plus the first "
    "1,000 characters of each uploaded document (the redacted excerpt ArogyaRakshak keeps). "
    "'Missing' means not found there — a longer document may still contain it."
)


class ReadinessReport(BaseModel):
    evidence_scope_note: str = EVIDENCE_SCOPE_NOTE
    items: List[ReadinessItemResult]
    present_count: int
    missing_count: int
    needs_clinical_confirmation_count: int
    rejected_by_reviewer_count: int
    ready_to_submit: bool
    recommended_actions: List[str]
    disclaimer: str = READINESS_DISCLAIMER
    baseline_source: str = BASELINE_SOURCE


def _keyword_hits(text: str, keywords: Sequence[str]) -> List[str]:
    hits = []
    for kw in keywords:
        pattern = re.compile(rf"(?<!\w){re.escape(kw)}(?!\w)", re.IGNORECASE)
        if pattern.search(text or ""):
            hits.append(kw)
    return hits


def _presence(item: ChecklistItem, case: CaseEvidence):
    rule = item.evidence_rule
    if rule.kind == "entity":
        found = case.entities.get(rule.entity_type or "", [])
        if found:
            return "EXTRACTED_ENTITY", [
                ItemEvidence(kind=rule.entity_type or "", reference=f["value"][:120], provenance="AI_DERIVED")
                for f in found[:3]
            ]
        return None, []
    if rule.kind == "case_total":
        if case.case_total > 0:
            return "CASE_TOTAL", [
                ItemEvidence(kind="case_total", reference=f"{case.case_total:,.2f}", provenance="AI_DERIVED")
            ]
        return None, []
    hits = _keyword_hits(case.document_text, rule.keywords)
    if hits:
        return "KEYWORD_MATCH", [
            ItemEvidence(kind="document_keyword", reference=h, provenance="AI_DERIVED") for h in hits[:5]
        ]
    return None, []


_STATUS_HEADLINE = {
    "PRESENT": "was found in the case",
    "MISSING": "was not found in the case",
    "NEEDS_CLINICAL_CONFIRMATION": "was found, but a clinician must confirm the clinical fact",
    "CONFIRMED_BY_REVIEWER": "was confirmed by a named reviewer",
    "REJECTED_BY_REVIEWER": "was not confirmed by the reviewer",
    "REVIEWER_COULD_NOT_DETERMINE": "could not be determined by the reviewer",
}


def explain_item(
    item: ChecklistItem,
    origin: str,
    status: str,
    strength: Optional[str],
    evidence: Sequence[ItemEvidence],
    decision: Optional[FactDecisionRef],
    entity_sources: Optional[Dict[str, Optional[str]]] = None,
) -> Explanation:
    """Why this checklist item has this status — from the rule that ran and the evidence it
    found. `entity_sources` maps an evidence reference to its source document name when the
    case recorded one; a missing entry is reported "not recorded"."""
    rule = item.evidence_rule
    entity_sources = entity_sources or {}
    rules: List[RuleUsed] = []
    if rule.kind == "entity":
        rules.append(RuleUsed(
            kind="ENTITY_PRESENCE_RULE",
            name=f"Present if at least one extracted '{rule.entity_type}' entity exists",
            facts=[fact("Entity type searched", rule.entity_type), fact("Rule origin", origin.replace("_", " ").lower())],
        ))
    elif rule.kind == "case_total":
        rules.append(RuleUsed(
            kind="CASE_TOTAL_RULE",
            name="Present if the case's extracted billing total is above zero",
            facts=[fact("Rule origin", origin.replace("_", " ").lower())],
        ))
    else:
        rules.append(RuleUsed(
            kind="KEYWORD_RULE",
            name="Present if any listed keyword appears in the stored document excerpts",
            facts=[
                fact("Keywords searched", ", ".join(rule.keywords)),
                fact("Matched keywords", ", ".join(e.reference for e in evidence) or "none"),
                fact("Where searched", EVIDENCE_SCOPE_NOTE),
                fact("Rule origin", origin.replace("_", " ").lower()),
            ],
        ))

    ev_items = [
        EvidenceItem(
            label=e.kind.replace("_", " "),
            value=e.reference,
            provenance={
                "AI_DERIVED": ProvenanceClass.OCR_EXTRACTED,
                "HUMAN_REVIEWED": ProvenanceClass.HUMAN_REVIEWED,
            }.get(e.provenance, ProvenanceClass.NOT_RECORDED),
            document=entity_sources.get(e.reference),
            source_text=None,
        )
        for e in evidence
    ]

    undetermined: List[Undetermined] = []
    if status == "MISSING":
        undetermined.append(Undetermined(
            code="NOT_FOUND_IN_SEARCHED_SCOPE",
            reason="Nothing matching the rule was found in what was searched. " + EVIDENCE_SCOPE_NOTE,
        ))
    if item.clinical_fact:
        if decision is None or decision.decision == "PENDING":
            undetermined.append(Undetermined(
                code="CLINICAL_FACT_UNCONFIRMED",
                reason="Software never confirms a clinical fact; no named reviewer has decided this one yet.",
            ))
        else:
            rules.append(RuleUsed(
                kind="REVIEWER_DECISION",
                name=f"Reviewer decision: {decision.decision}",
                facts=[
                    fact("Reviewer", decision.reviewer_name),
                    fact("Verification", decision.reviewer_verification_label),
                    fact("Conflict-of-interest label", decision.coi_label),
                    fact("Decided at", decision.decided_at),
                ],
            ))
    if strength == "KEYWORD_MATCH":
        undetermined.append(Undetermined(
            code="KEYWORD_ONLY_EVIDENCE",
            reason="A keyword match shows the word appears, not that the document contains the documentation itself.",
        ))
    if strength == "REVIEWER_DECISION":
        trust = TrustState(code="HUMAN_REVIEWED", label="Decided by a named reviewer")
    elif strength is None:
        trust = TrustState(code="NO_EVIDENCE", label="No evidence found")
    elif strength == "KEYWORD_MATCH":
        trust = TrustState(code="WEAK_EVIDENCE", label="Weaker evidence: keyword found in document excerpt")
    else:
        trust = TrustState(code="MACHINE_EXTRACTED", label="Machine-extracted evidence; contents not verified")

    return Explanation(
        finding_type="DAAVISETU_ITEM",
        headline=f"“{item.label}” {_STATUS_HEADLINE.get(status, 'has this status')}.",
        evidence=ev_items,
        rules=rules,
        trust=trust,
        undetermined=undetermined,
    )


def evaluate_readiness(
    case: CaseEvidence,
    baseline_items: Sequence[ChecklistItem],
    playbook_items: Sequence[ChecklistItem] = (),
    fact_decisions: Optional[Dict[str, FactDecisionRef]] = None,
) -> ReadinessReport:
    fact_decisions = fact_decisions or {}
    # Source document of each extracted entity, when the case recorded one (explanations).
    entity_sources = {
        f["value"][:120]: f.get("source_file")
        for found in case.entities.values()
        for f in found
        if f.get("source_file")
    }
    results: List[ReadinessItemResult] = []
    combined = [(i, "BASELINE") for i in baseline_items] + [
        (i, "INSTITUTION_PLAYBOOK") for i in playbook_items
    ]
    seen = set()
    for item, origin in combined:
        if item.item_id in seen:
            continue
        seen.add(item.item_id)
        strength, evidence = _presence(item, case)
        decision = fact_decisions.get(item.item_id) if item.clinical_fact else None

        if item.clinical_fact and decision and decision.decision != "PENDING":
            status: ItemStatus = {
                "CONFIRMED": "CONFIRMED_BY_REVIEWER",
                "REJECTED": "REJECTED_BY_REVIEWER",
                "CANNOT_DETERMINE": "REVIEWER_COULD_NOT_DETERMINE",
            }[decision.decision]
            strength = "REVIEWER_DECISION"
        elif strength is None:
            status = "MISSING"
        elif item.clinical_fact:
            status = "NEEDS_CLINICAL_CONFIRMATION"
        else:
            status = "PRESENT"

        results.append(
            ReadinessItemResult(
                item_id=item.item_id,
                label=item.label,
                status=status,
                evidence_strength=strength,
                evidence=evidence,
                clinical_fact=item.clinical_fact,
                clinical_fact_question=item.clinical_fact_question,
                clinical_decision=decision,
                origin=origin,  # type: ignore[arg-type]
                note=item.note,
                explanation=explain_item(item, origin, status, strength, evidence, decision, entity_sources),
            )
        )

    missing = [r for r in results if r.status == "MISSING"]
    needs = [r for r in results if r.status == "NEEDS_CLINICAL_CONFIRMATION"]
    unresolved = [r for r in results if r.status in ("REJECTED_BY_REVIEWER", "REVIEWER_COULD_NOT_DETERMINE")]
    actions: List[str] = []
    if missing:
        actions.append(
            "Request the missing documentation before submission (first check it is not already "
            "further into a document you uploaded): " + "; ".join(r.label for r in missing) + "."
        )
    if needs:
        actions.append(
            "Ask a clinician to confirm these facts before relying on them in the claim: "
            + "; ".join(r.label for r in needs) + "."
        )
    if unresolved:
        actions.append(
            "A reviewer did not confirm: " + "; ".join(r.label for r in unresolved)
            + ". Do not state these as facts in the claim."
        )
    if not actions:
        actions.append("All listed documentation was found. Review each document yourself before submission.")

    return ReadinessReport(
        items=results,
        present_count=sum(1 for r in results if r.status in ("PRESENT", "CONFIRMED_BY_REVIEWER")),
        missing_count=len(missing),
        needs_clinical_confirmation_count=len(needs),
        rejected_by_reviewer_count=sum(1 for r in results if r.status == "REJECTED_BY_REVIEWER"),
        ready_to_submit=not (missing or needs or unresolved),
        recommended_actions=actions,
    )


def render_readiness_text(report: ReadinessReport, playbook_label: Optional[str] = None) -> str:
    """Plain-text rendering for the claim package ZIP."""
    lines = [
        "PRE-AUTHORIZATION READINESS CHECKLIST",
        f"Guidance used: {playbook_label or 'DaaviSetu generic baseline only'}",
        f"Baseline source: {report.baseline_source}",
        f"Evidence searched: {report.evidence_scope_note}",
        "",
    ]
    for r in report.items:
        lines.append(f"[{r.status}] {r.label}")
        if r.evidence:
            lines.append(
                "    evidence: " + ", ".join(f"{e.kind}: {e.reference} ({e.provenance})" for e in r.evidence)
            )
        if r.clinical_decision and r.clinical_decision.decision != "PENDING":
            d = r.clinical_decision
            lines.append(
                f"    reviewer decision: {d.decision} by {d.reviewer_name or 'reviewer'}"
                f" ({d.reviewer_verification_label}; COI: {d.coi_label}) at {d.decided_at}"
            )
    lines += ["", "Recommended actions:"] + [f"  - {a}" for a in report.recommended_actions]
    lines += ["", report.disclaimer]
    return "\n".join(lines)
