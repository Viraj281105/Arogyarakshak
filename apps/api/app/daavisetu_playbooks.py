"""
DaaviSetu institution playbooks and preauth readiness — persistence (ADR-011).

Isolation: every playbook read or write is filtered by the caller's own institution id.
A playbook id belonging to another institution is "not found", never "forbidden", so ids
cannot be probed across hospitals. There is no public or cross-institution listing.
"""

import re
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from daavisetu.readiness import (
    BASELINE_ITEMS,
    CaseEvidence,
    ChecklistItem,
    FactDecisionRef,
    ReadinessReport,
    evaluate_readiness,
    validate_items,
)
from kadi.clinical_review.evidence import EntityRecord

from app.clinical.serializers import coi_label
from app.models import DaaviSetuInstitution, DaaviSetuPlaybook, KadiClinicalFactConfirmation

_KEY = re.compile(r"^[a-z0-9][a-z0-9_\-]{2,60}$")
_ASSERTION = re.compile(
    r"\b(?:patient|claimant|insured|member|he|she)\s+(?:had|has|have|was|were|is|underwent|failed|received|took)\b",
    re.IGNORECASE,
)
OPEN_PLAYBOOK_STATES = ("DRAFT",)


def _parse_items(raw_items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    try:
        items = validate_items([ChecklistItem(**i) for i in raw_items])
    except (ValidationError, ValueError, TypeError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid playbook items: {e}")
    baseline_ids = {i.item_id for i in BASELINE_ITEMS}
    clash = [i.item_id for i in items if i.item_id in baseline_ids]
    if clash:
        raise HTTPException(status_code=422, detail=f"item_id collides with a baseline item: {clash}")
    return [i.model_dump() for i in items]


def _validate_evidence_list(values: Sequence[str]) -> List[str]:
    cleaned = [" ".join(str(v).split())[:200] for v in values if str(v).strip()]
    if len(cleaned) > 30:
        raise HTTPException(status_code=422, detail="At most 30 commonly requested evidence entries.")
    bad = [v for v in cleaned if _ASSERTION.search(v)]
    if bad:
        raise HTTPException(
            status_code=422,
            detail="commonly_requested_evidence must describe documents, not assert facts about a claimant.",
        )
    return cleaned


def _apply(pb: DaaviSetuPlaybook, data: Dict[str, Any]) -> None:
    for field in ("title", "insurer", "procedure_category", "source_provenance", "owner"):
        value = (data.get(field) or "").strip()
        if not value:
            raise HTTPException(status_code=422, detail=f"{field} is required.")
        setattr(pb, field, value[:300])
    pb.policy_product = (data.get("policy_product") or "").strip()[:200] or None
    pb.internal_notes = (data.get("internal_notes") or "").strip()[:2000] or None
    pb.items = _parse_items(data.get("items") or [])
    pb.commonly_requested_evidence = _validate_evidence_list(data.get("commonly_requested_evidence") or [])
    effective: date = data["effective_date"]
    due: date = data["review_due_date"]
    if due <= effective:
        raise HTTPException(status_code=422, detail="review_due_date must be after effective_date.")
    pb.effective_date = effective
    pb.review_due_date = due


async def create_playbook(db: AsyncSession, institution: DaaviSetuInstitution, data: Dict[str, Any], *, status_value: str = "DRAFT") -> DaaviSetuPlaybook:
    key = (data.get("playbook_key") or "").strip()
    if not _KEY.match(key):
        raise HTTPException(status_code=422, detail="playbook_key must be a lowercase slug (3-61 chars).")
    exists = await db.execute(
        select(func.count()).select_from(DaaviSetuPlaybook).where(
            DaaviSetuPlaybook.institution_id == institution.id, DaaviSetuPlaybook.playbook_key == key
        )
    )
    if exists.scalar_one():
        raise HTTPException(status_code=409, detail="A playbook with this key exists; create a new version instead.")
    pb = DaaviSetuPlaybook(
        id=f"PB-{uuid.uuid4().hex[:12]}", institution_id=institution.id, playbook_key=key, version=1, status=status_value
    )
    _apply(pb, data)
    db.add(pb)
    return pb


async def own_playbook(db: AsyncSession, institution: DaaviSetuInstitution, playbook_id: str) -> DaaviSetuPlaybook:
    pb = await db.get(DaaviSetuPlaybook, playbook_id)
    if pb is None or pb.institution_id != institution.id:
        raise HTTPException(status_code=404, detail="Playbook not found.")
    return pb


async def list_playbooks(db: AsyncSession, institution: DaaviSetuInstitution) -> List[DaaviSetuPlaybook]:
    rows = await db.execute(
        select(DaaviSetuPlaybook)
        .where(DaaviSetuPlaybook.institution_id == institution.id)
        .order_by(DaaviSetuPlaybook.playbook_key, DaaviSetuPlaybook.version)
    )
    return list(rows.scalars().all())


def update_playbook(pb: DaaviSetuPlaybook, data: Dict[str, Any]) -> None:
    if pb.status != "DRAFT":
        raise HTTPException(status_code=409, detail=f"A {pb.status} playbook is immutable; create a new version.")
    _apply(pb, data)


async def activate_playbook(db: AsyncSession, pb: DaaviSetuPlaybook) -> None:
    if pb.status != "DRAFT":
        raise HTTPException(status_code=409, detail=f"Only a DRAFT playbook can be activated (current: {pb.status}).")
    previous = await db.execute(
        select(DaaviSetuPlaybook).where(
            DaaviSetuPlaybook.institution_id == pb.institution_id,
            DaaviSetuPlaybook.playbook_key == pb.playbook_key,
            DaaviSetuPlaybook.status == "ACTIVE",
        )
    )
    for old in previous.scalars().all():
        old.status = "SUPERSEDED"
    pb.status = "ACTIVE"
    pb.activated_at = datetime.utcnow()


def retire_playbook(pb: DaaviSetuPlaybook) -> None:
    if pb.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Only an ACTIVE playbook can be retired.")
    pb.status = "RETIRED"
    pb.retired_at = datetime.utcnow()


async def new_playbook_version(db: AsyncSession, pb: DaaviSetuPlaybook) -> DaaviSetuPlaybook:
    open_count = await db.execute(
        select(func.count()).select_from(DaaviSetuPlaybook).where(
            DaaviSetuPlaybook.institution_id == pb.institution_id,
            DaaviSetuPlaybook.playbook_key == pb.playbook_key,
            DaaviSetuPlaybook.status.in_(OPEN_PLAYBOOK_STATES),
        )
    )
    if open_count.scalar_one():
        raise HTTPException(status_code=409, detail="This playbook already has a draft version.")
    latest = await db.execute(
        select(func.max(DaaviSetuPlaybook.version)).where(
            DaaviSetuPlaybook.institution_id == pb.institution_id, DaaviSetuPlaybook.playbook_key == pb.playbook_key
        )
    )
    draft = DaaviSetuPlaybook(
        id=f"PB-{uuid.uuid4().hex[:12]}",
        institution_id=pb.institution_id,
        playbook_key=pb.playbook_key,
        version=(latest.scalar_one() or pb.version) + 1,
        title=pb.title,
        insurer=pb.insurer,
        policy_product=pb.policy_product,
        procedure_category=pb.procedure_category,
        items=list(pb.items or []),
        commonly_requested_evidence=list(pb.commonly_requested_evidence or []),
        internal_notes=pb.internal_notes,
        source_provenance=pb.source_provenance,
        owner=pb.owner,
        effective_date=pb.effective_date,
        review_due_date=pb.review_due_date,
        status="DRAFT",
        supersedes_playbook_id=pb.id,
    )
    db.add(draft)
    return draft


def playbook_view(pb: DaaviSetuPlaybook, institution_name: Optional[str] = None) -> Dict[str, Any]:
    return {
        "playbook_id": pb.id,
        "institution_id": pb.institution_id,
        "institution_name": institution_name,
        "playbook_key": pb.playbook_key,
        "version": pb.version,
        "title": pb.title,
        "insurer": pb.insurer,
        "policy_product": pb.policy_product,
        "procedure_category": pb.procedure_category,
        "items": pb.items,
        "commonly_requested_evidence": pb.commonly_requested_evidence,
        "internal_notes": pb.internal_notes,
        "source_provenance": pb.source_provenance,
        "owner": pb.owner,
        "effective_date": pb.effective_date,
        "review_due_date": pb.review_due_date,
        "is_past_review_date": pb.review_due_date < date.today(),
        "status": pb.status,
        "supersedes_playbook_id": pb.supersedes_playbook_id,
        "visibility": "Private to this institution. Not shared with any other hospital or insurer.",
        "created_at": pb.created_at,
    }


def playbook_items(pb: DaaviSetuPlaybook) -> List[ChecklistItem]:
    return [ChecklistItem(**i) for i in (pb.items or [])]


def ensure_applicable(pb: DaaviSetuPlaybook) -> None:
    if pb.status != "ACTIVE":
        raise HTTPException(status_code=409, detail=f"Playbook is {pb.status}; only an ACTIVE playbook can be applied.")
    if pb.review_due_date < date.today():
        raise HTTPException(
            status_code=409,
            detail="This playbook is past its review date. Review it and publish a new version before using it.",
        )
    if pb.effective_date > date.today():
        raise HTTPException(status_code=409, detail="This playbook is not effective yet.")


def case_evidence(entities: Sequence[EntityRecord], case_total: float) -> CaseEvidence:
    grouped: Dict[str, List[Dict[str, str]]] = {}
    text_parts: List[str] = []
    for e in entities:
        if e.type == "document_text":
            text_parts.append(e.value or "")
            continue
        grouped.setdefault(e.type, []).append({"id": e.id, "value": e.name})
    return CaseEvidence(entities=grouped, document_text="\n".join(text_parts), case_total=case_total or 0.0)


def decision_refs(latest: Dict[str, KadiClinicalFactConfirmation]) -> Dict[str, FactDecisionRef]:
    refs: Dict[str, FactDecisionRef] = {}
    for key, fact in latest.items():
        snap = fact.reviewer_snapshot or {}
        refs[key] = FactDecisionRef(
            decision=fact.decision,
            fact_id=fact.id,
            reviewer_name=snap.get("name"),
            reviewer_verification_label=snap.get("verification_label"),
            coi_label=coi_label(fact.coi_category),
            decided_at=fact.decided_at.isoformat() if fact.decided_at else None,
        )
    return refs


def build_report(
    entities: Sequence[EntityRecord],
    case_total: float,
    latest: Dict[str, KadiClinicalFactConfirmation],
    pb: Optional[DaaviSetuPlaybook],
) -> ReadinessReport:
    return evaluate_readiness(
        case_evidence(entities, case_total),
        BASELINE_ITEMS,
        playbook_items(pb) if pb else [],
        decision_refs(latest),
    )
