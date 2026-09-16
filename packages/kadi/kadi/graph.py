"""
Kadi case knowledge graph (#86).

A typed node-link projection of one case's stored Kadi entities: a hospital stay linked to
its hospital, diagnoses, procedures, medicines and bill lines. It is computed on request
from the existing Postgres rows — **there is no graph database (GraphDB/Neo4j)**; a case
holds a handful of documents, so a separate graph store would add infrastructure without
adding capability.

Every edge carries the evidence it was derived from, and only three kinds are used:

- ``case_membership``          — the entity was extracted into this case
- ``name_match_same_document`` — a procedure/medicine and a bill line with matching names
                                 (resolver confidence >= threshold, no conflicts) extracted
                                 from the same source document
- ``pending_resolution_decision`` — Kadi's resolver could not decide whether two entities
                                 are the same and is waiting for the user

"Cross-lingual" means an entity node carries every surface form merged into it (for
example "Crocin" and "क्रोसिन") as aliases, via entity resolution.

No clinical relationship is inferred: there are no "treats" or "indicated for" edges.
Asserting that a medicine treats a diagnosis would be a medical claim this system has no
evidence for.
"""

from typing import Any, Dict, List, Literal, Optional, Sequence

from pydantic import BaseModel, Field

from kadi.resolution.resolver import score_pair

EvidenceKind = Literal["case_membership", "name_match_same_document", "pending_resolution_decision"]

RELATION_BY_TYPE = {
    "hospital": "AT_HOSPITAL",
    "diagnosis": "RECORDED_DIAGNOSIS",
    "procedure": "RECORDED_PROCEDURE",
    "medicine": "RECORDED_MEDICINE",
    "billing_item": "BILLED_ITEM",
}

GRAPH_LIMITATIONS = [
    "A case is modelled as a single hospital stay; multiple admissions in one case are not separated.",
    "No clinical relationships (e.g. medicine treats diagnosis) are inferred; only extraction, "
    "same-document name matches and pending resolution questions become edges.",
    "BILLED_AS links depend on name similarity within one document and can miss bill lines "
    "worded very differently from the clinical entity.",
    "This is an on-request projection of stored entities, not a graph database.",
]


class EntityRecord(BaseModel):
    id: str
    name: str
    type: str
    value: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class PendingLink(BaseModel):
    decision_id: str
    mention_entity_id: str
    candidate_entity_id: str
    confidence: float


class StayInfo(BaseModel):
    case_id: str
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None


class EdgeEvidence(BaseModel):
    kind: EvidenceKind
    source_files: List[str] = Field(default_factory=list)
    score: Optional[float] = None
    detail: str = ""


class GraphNode(BaseModel):
    id: str
    kind: str
    label: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    aliases: List[str] = Field(default_factory=list)
    source_files: List[str] = Field(default_factory=list)


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str
    evidence: List[EdgeEvidence]


class CaseGraph(BaseModel):
    case_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    stats: Dict[str, int]
    limitations: List[str]


def entity_source_files(entity: EntityRecord) -> List[str]:
    files = [entity.meta.get("source_file")]
    for mention in entity.meta.get("mentions") or []:
        if isinstance(mention, dict):
            files.append(mention.get("source_file"))
    return [f for f in dict.fromkeys(files) if isinstance(f, str) and f]


def entity_aliases(entity: EntityRecord) -> List[str]:
    names = [m.get("name") for m in entity.meta.get("mentions") or [] if isinstance(m, dict)]
    return [n for n in dict.fromkeys(names) if isinstance(n, str) and n and n != entity.name]


def build_case_graph(
    stay: StayInfo,
    entities: Sequence[EntityRecord],
    pending: Sequence[PendingLink] = (),
    billed_as_threshold: float = 0.90,
) -> CaseGraph:
    stay_id = f"STAY-{stay.case_id}"
    dates_known = bool(stay.admission_date or stay.discharge_date)
    nodes: List[GraphNode] = [
        GraphNode(
            id=stay_id,
            kind="hospital_stay",
            label="Hospital stay",
            attributes={
                "admission_date": stay.admission_date,
                "discharge_date": stay.discharge_date,
                "dates_status": "RECORDED" if dates_known else "UNKNOWN",
            },
        )
    ]
    edges: List[GraphEdge] = []
    graph_entities = [e for e in entities if e.type in RELATION_BY_TYPE]
    node_ids = {stay_id}

    for entity in graph_entities:
        sources = entity_source_files(entity)
        nodes.append(
            GraphNode(
                id=entity.id,
                kind=entity.type,
                label=entity.name,
                attributes={"value": entity.value},
                aliases=entity_aliases(entity),
                source_files=sources,
            )
        )
        node_ids.add(entity.id)
        edges.append(
            GraphEdge(
                source=stay_id,
                target=entity.id,
                relation=RELATION_BY_TYPE[entity.type],
                evidence=[EdgeEvidence(kind="case_membership", source_files=sources)],
            )
        )

    bill_lines = [e for e in graph_entities if e.type == "billing_item"]
    for clinical in (e for e in graph_entities if e.type in ("procedure", "medicine")):
        clinical_sources = set(entity_source_files(clinical))
        for line in bill_lines:
            shared = sorted(clinical_sources & set(entity_source_files(line)))
            if not shared:
                continue
            pair = score_pair(clinical.name, line.name, clinical.type, enabled_signals=frozenset({"lexical", "phonetic"}))
            if pair.conflicts or pair.confidence < billed_as_threshold:
                continue
            edges.append(
                GraphEdge(
                    source=clinical.id,
                    target=line.id,
                    relation="BILLED_AS",
                    evidence=[
                        EdgeEvidence(
                            kind="name_match_same_document",
                            source_files=shared,
                            score=pair.confidence,
                            detail="lexical + phonetic name match",
                        )
                    ],
                )
            )

    for link in pending:
        if link.mention_entity_id in node_ids and link.candidate_entity_id in node_ids:
            edges.append(
                GraphEdge(
                    source=link.mention_entity_id,
                    target=link.candidate_entity_id,
                    relation="POSSIBLY_SAME_AS",
                    evidence=[
                        EdgeEvidence(
                            kind="pending_resolution_decision",
                            score=link.confidence,
                            detail=f"awaiting user confirmation ({link.decision_id})",
                        )
                    ],
                )
            )

    stats: Dict[str, int] = {"nodes": len(nodes), "edges": len(edges)}
    for node in nodes:
        stats[f"nodes.{node.kind}"] = stats.get(f"nodes.{node.kind}", 0) + 1
    for edge in edges:
        stats[f"edges.{edge.relation}"] = stats.get(f"edges.{edge.relation}", 0) + 1

    return CaseGraph(
        case_id=stay.case_id,
        nodes=nodes,
        edges=edges,
        stats=stats,
        limitations=list(GRAPH_LIMITATIONS),
    )
