"""
Evidence packets for human review (ADR-011).

A reviewer never browses a case. At request time the case holder chooses which kinds of
case context to share; the server freezes exactly those items into an evidence packet,
and that packet is the only case data the reviewer can ever see. It is also the record
of "what evidence was made available", which a finalized statement must cite from.
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

from kadi.redaction import redact_pii

from .medicine_trust import decide_medicine_trust
from .types import ProvenanceClass, SourceModule

SHAREABLE_ENTITY_TYPES = frozenset(
    {"diagnosis", "procedure", "medicine", "billing_item", "document_text", "hospital"}
)

DEFAULT_SCOPE_BY_MODULE: Dict[str, List[str]] = {
    SourceModule.BILLNYAY.value: ["diagnosis", "procedure", "billing_item", "document_text"],
    SourceModule.BIMANYAY.value: ["diagnosis", "procedure", "document_text"],
    SourceModule.DAAVISETU.value: ["diagnosis", "procedure", "document_text"],
    SourceModule.DAWACHECK.value: ["medicine", "diagnosis"],
    SourceModule.KADI.value: ["diagnosis", "procedure", "medicine", "document_text"],
}

MAX_EVIDENCE_ITEMS = 60
MAX_EVIDENCE_VALUE_CHARS = 1000


@dataclass(frozen=True)
class EntityRecord:
    id: str
    type: str
    name: str
    value: Optional[str]
    meta: Optional[Dict[str, Any]]


@dataclass(frozen=True)
class SupplementaryItem:
    """Non-entity evidence the server itself attaches (a module's machine-derived finding,
    or a denial record the case holder entered)."""

    item_id: str
    kind: str
    label: str
    value: str
    provenance: ProvenanceClass
    source: str


def resolve_scope(source_module: str, requested: Optional[Sequence[str]]) -> List[str]:
    if requested is None:
        return list(DEFAULT_SCOPE_BY_MODULE.get(source_module, DEFAULT_SCOPE_BY_MODULE["kadi"]))
    scope = [s for s in dict.fromkeys(requested)]
    unknown = [s for s in scope if s not in SHAREABLE_ENTITY_TYPES]
    if unknown:
        raise ValueError(
            f"evidence_scope may only contain {sorted(SHAREABLE_ENTITY_TYPES)}; got {unknown}"
        )
    if not scope:
        raise ValueError("evidence_scope must contain at least one evidence type.")
    return scope


def _entity_provenance(entity: EntityRecord) -> ProvenanceClass:
    if entity.type == "medicine":
        # One trust decision for medicines (kadi.clinical_review.medicine_trust): a
        # partial human reading does not make an otherwise-uncertain entry reviewed.
        decision = decide_medicine_trust(entity.name, entity.meta)
        return ProvenanceClass(decision.name_provenance)
    meta = entity.meta or {}
    transcription = meta.get("human_transcription") if isinstance(meta, dict) else None
    if isinstance(transcription, dict) and transcription.get("status") == "RESOLVED":
        return ProvenanceClass.HUMAN_REVIEWED
    return ProvenanceClass.AI_DERIVED


def _entity_source(entity: EntityRecord) -> str:
    meta = entity.meta or {}
    src = meta.get("source") if isinstance(meta, dict) else None
    if entity.type == "billing_item":
        return "Bill line read by Kadi OCR/line-item parser"
    if entity.type == "document_text":
        return "Redacted document excerpt extracted by Kadi"
    if src == "abdm_fhir":
        return "Imported from a patient-supplied ABDM FHIR bundle"
    return "Extracted from uploaded document by Kadi"


def _display_value(entity: EntityRecord) -> str:
    meta = entity.meta or {}
    if entity.type == "medicine" and isinstance(meta, dict):
        uncertainty = meta.get("ocr_uncertainty")
        if isinstance(uncertainty, dict) and uncertainty.get("status") == "UNRESOLVED":
            dosage = meta.get("dosage")
            base = f"{entity.name} ({dosage})" if dosage else entity.name
            return f"{base} (unsettled: part of this entry was read with low confidence and no human has read it)"
    transcription = meta.get("human_transcription") if isinstance(meta, dict) else None
    if isinstance(transcription, dict) and transcription.get("status") == "RESOLVED":
        return str(transcription.get("value") or entity.name)
    if isinstance(transcription, dict) and transcription.get("status") == "NOT_APPLIED":
        return (
            f"{entity.name} (unsettled: human readers read '{transcription.get('human_reading')}', "
            "which could not be matched to this extracted entry)"
        )
    if entity.type in ("billing_item",):
        return f"{entity.name} — charged {entity.value}" if entity.value else entity.name
    if entity.type == "document_text":
        return entity.value or ""
    if entity.type == "medicine":
        dosage = meta.get("dosage") if isinstance(meta, dict) else None
        return f"{entity.name} ({dosage})" if dosage else entity.name
    return entity.name


def build_evidence_packet(
    entities: Iterable[EntityRecord],
    scope: Sequence[str],
    supplementary: Iterable[SupplementaryItem] = (),
) -> List[Dict[str, Any]]:
    """Freezes the in-scope case context into reviewer-visible evidence items.

    Every value passes through PII redaction again (defence in depth — the document
    excerpt is already redacted at ingestion) and is length-bounded.
    """
    scope_set = set(scope)
    items: List[Dict[str, Any]] = []
    for entity in entities:
        if entity.type not in scope_set:
            continue
        value = redact_pii(_display_value(entity))[:MAX_EVIDENCE_VALUE_CHARS]
        items.append(
            {
                "item_id": entity.id,
                "kind": entity.type,
                "label": entity.type.replace("_", " ").title(),
                "value": value,
                "provenance": _entity_provenance(entity).value,
                "source": _entity_source(entity),
            }
        )
        if len(items) >= MAX_EVIDENCE_ITEMS:
            break

    for extra in supplementary:
        items.append(
            {
                "item_id": extra.item_id,
                "kind": extra.kind,
                "label": extra.label,
                "value": redact_pii(extra.value)[:MAX_EVIDENCE_VALUE_CHARS],
                "provenance": extra.provenance.value,
                "source": extra.source,
            }
        )
    return items


def build_coi_context(
    entities: Iterable[EntityRecord], source_module: str, insurer_name: Optional[str]
) -> Dict[str, Any]:
    """The minimum a reviewer needs to declare a conflict of interest BEFORE seeing any
    clinical evidence: which hospital and insurer are involved. Nothing clinical."""
    hospitals = [e.name for e in entities if e.type == "hospital" and e.name]
    return {
        "source_module": source_module,
        "hospital_names": sorted(set(hospitals))[:3],
        "insurer_name": insurer_name,
        "note": (
            "Declare any relationship with this hospital, this insurer or the patient before "
            "opening the evidence."
        ),
    }
