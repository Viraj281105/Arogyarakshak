"""
Explanation trail — the shared, deterministic "Why am I seeing this?" record (ADR-015).

Every finding a user sees (a BillNyay line, a DawaCheck medicine comparison, a DaaviSetu
readiness item, a BimaNyay deadline) is produced by deterministic code from data the
system already holds. This module defines the one structured shape those findings share;
the OWNING package builds the instance next to the decision (`billnyay.explain`,
`dawacheck.explain`, `daavisetu.readiness`, `bimanyay.tracker`), from the same values the
decision used. No builder calls an LLM and none infers a reason it was not told.

Honesty rules enforced here, not left to each builder:
  * a fact whose value the system did not record carries ``value=None`` and is rendered
    "not recorded" — it is never filled in with a plausible guess;
  * ``not_recorded`` is derived from the facts (single source of truth), so a client can
    show exactly what is missing without re-deriving it;
  * what could not be determined is a first-class list (``undetermined``), with a code
    and a plain reason, never an empty string.
"""

from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

NOT_RECORDED_TEXT = "not recorded"


class ProvenanceClass(str, Enum):
    """Where a piece of evidence came from. Only what the system actually knows."""

    OCR_EXTRACTED = "OCR_EXTRACTED"  # read from an uploaded document by OCR / the extractor
    LLM_NORMALISED = "LLM_NORMALISED"  # the extractor's wording may differ from the OCR reading
    HUMAN_REVIEWED = "HUMAN_REVIEWED"  # settled by independent human reading / a named reviewer
    USER_ENTERED = "USER_ENTERED"  # typed or declared by the person using the app
    REFERENCE_DATA = "REFERENCE_DATA"  # a row of a bundled public reference table
    RULE_COMPUTED = "RULE_COMPUTED"  # derived by a fixed rule from the values above
    NOT_RECORDED = "NOT_RECORDED"  # the system did not record where this came from


PROVENANCE_LABELS = {
    ProvenanceClass.OCR_EXTRACTED: "Read from your document (OCR / extraction)",
    ProvenanceClass.LLM_NORMALISED: "Wording may have been normalised by the extractor",
    ProvenanceClass.HUMAN_REVIEWED: "Reviewed by a human",
    ProvenanceClass.USER_ENTERED: "Entered by you",
    ProvenanceClass.REFERENCE_DATA: "Bundled public reference table",
    ProvenanceClass.RULE_COMPUTED: "Computed by a fixed rule",
    ProvenanceClass.NOT_RECORDED: "Origin not recorded",
}


class Fact(BaseModel):
    """One labelled value. ``value=None`` means the system did not record it."""

    label: str
    value: Optional[str] = None


class EvidenceItem(BaseModel):
    """A piece of source evidence the finding rests on."""

    label: str
    value: Optional[str] = None
    provenance: ProvenanceClass = ProvenanceClass.NOT_RECORDED
    # The uploaded document's name, when the system recorded it (None -> "not recorded").
    document: Optional[str] = None
    # The short text/line the value was read from, when recorded.
    source_text: Optional[str] = None


RuleKind = Literal[
    "REFERENCE_TABLE_ROW",
    "PRICE_BASIS",
    "KEYWORD_RULE",
    "ENTITY_PRESENCE_RULE",
    "CASE_TOTAL_RULE",
    "REVIEWER_DECISION",
    "STATUTORY_PERIOD",
    "COMPUTATION",
]


class RuleUsed(BaseModel):
    """The exact rule or reference row applied."""

    kind: RuleKind
    name: str
    facts: List[Fact] = Field(default_factory=list)
    # A citation recorded alongside the rule (e.g. a statute/rule number, a table version).
    source: Optional[str] = None


class TrustState(BaseModel):
    code: str
    label: str
    detail: Optional[str] = None


class Undetermined(BaseModel):
    """Something the system could not establish, and why."""

    code: str
    reason: str


class Explanation(BaseModel):
    finding_type: Literal["BILLNYAY_LINE", "DAWACHECK_MEDICINE", "DAAVISETU_ITEM", "BIMANYAY_DEADLINE"]
    headline: str
    evidence: List[EvidenceItem] = Field(default_factory=list)
    rules: List[RuleUsed] = Field(default_factory=list)
    trust: TrustState
    undetermined: List[Undetermined] = Field(default_factory=list)
    # Derived: labels of every fact/evidence value the system did not record.
    not_recorded: List[str] = Field(default_factory=list)
    generated_by: str = "deterministic rules over stored data; no AI model was used to write this explanation"
    disclaimer: str = (
        "This shows how the result above was produced from the data ArogyaRakshak holds. It is not "
        "legal, medical or financial advice and does not predict any insurer's or hospital's decision."
    )

    @model_validator(mode="after")
    def _derive_not_recorded(self) -> "Explanation":
        missing: List[str] = []
        for ev in self.evidence:
            if ev.value is None:
                missing.append(ev.label)
            if ev.document is None and ev.provenance in (
                ProvenanceClass.OCR_EXTRACTED,
                ProvenanceClass.LLM_NORMALISED,
            ):
                missing.append(f"{ev.label}: source document")
        for rule in self.rules:
            for f in rule.facts:
                if f.value is None:
                    missing.append(f"{rule.name}: {f.label}")
        self.not_recorded = list(dict.fromkeys(missing))
        return self


def fact(label: str, value: object) -> Fact:
    """Builds a Fact; ``None`` or an empty string means "not recorded"."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return Fact(label=label, value=None)
    return Fact(label=label, value=str(value))


def render_plain_text(explanation: Explanation) -> str:
    """Plain-text rendering (mobile, copy/paste). Mirrors the structured fields exactly."""

    def v(value: Optional[str]) -> str:
        return value if value is not None else NOT_RECORDED_TEXT

    lines = [explanation.headline, "", f"Confidence / trust: {explanation.trust.label}"]
    if explanation.trust.detail:
        lines.append(f"  {explanation.trust.detail}")
    if explanation.evidence:
        lines += ["", "Source evidence:"]
        for e in explanation.evidence:
            doc = f" — document: {v(e.document)}" if e.provenance in (
                ProvenanceClass.OCR_EXTRACTED, ProvenanceClass.LLM_NORMALISED
            ) else ""
            lines.append(f"  - {e.label}: {v(e.value)} [{PROVENANCE_LABELS[e.provenance]}]{doc}")
    if explanation.rules:
        lines += ["", "Rule / reference used:"]
        for r in explanation.rules:
            lines.append(f"  - {r.name}" + (f" ({r.source})" if r.source else ""))
            lines += [f"      {f.label}: {v(f.value)}" for f in r.facts]
    if explanation.undetermined:
        lines += ["", "Could not be determined:"]
        lines += [f"  - {u.reason}" for u in explanation.undetermined]
    lines += ["", explanation.disclaimer]
    return "\n".join(lines)
