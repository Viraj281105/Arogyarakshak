"""
Kadi entity resolution — persistence (#31) and feedback calibration (#88).

The decision logic is pure and lives in ``packages/kadi/kadi/resolution``. This module
applies decisions to a case's stored entities:

- MERGE — no new entity; the mention is appended to the existing entity's
  ``meta["mentions"]`` (so every source document and script variant stays visible) and an
  ``auto_merged`` decision row is kept so the user can dispute it. Mentions whose names
  are identical after normalization merge silently, without a decision row.
- ASK   — the mention is stored as its own entity (nothing is lost while unanswered) and a
  ``pending`` decision row asks the user whether the two are the same.
- NEW   — the mention is stored as a new entity.

Feedback on a decision applies it (confirm -> fold the mention in; reject -> keep both;
dispute an automatic merge -> split it back out) and records the label that feeds the
bounded threshold recalibration in ``kadi.resolution.calibration``.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KadiCase, KadiEntity, KadiResolutionDecision, KadiThresholdCalibration
from kadi.resolution import (
    RESOLVABLE_ENTITY_TYPES,
    CandidateEntity,
    EntityMention,
    ResolutionThresholds,
    get_default_semantic_encoder,
    resolve_mention,
)
from kadi.resolution.calibration import CalibrationResult, LabeledOutcome, calibrate_thresholds
from kadi.resolution.similarity import normalize_surface

logger = logging.getLogger("arogyarakshak.api.kadi_resolution")

ENTITY_ID_PREFIX = {
    "billing_item": "ENT-BILL",
    "hospital": "ENT-HOSP",
    "diagnosis": "ENT-DIAG",
    "procedure": "ENT-PROC",
    "medicine": "ENT-MED",
    "document_text": "ENT-TEXT",
}

ALL_TYPES_SCOPE = "all_types"
_UNSET = object()


class DecisionAlreadyResolved(Exception):
    """Feedback was already given for this decision."""


class DecisionStale(Exception):
    """An entity the decision refers to no longer exists (e.g. merged by another answer)."""


@dataclass
class MentionInput:
    entity_type: str
    name: str
    value: Optional[str]
    meta: Dict[str, Any]


@dataclass
class ResolutionSummary:
    created: int = 0
    merged: int = 0
    pending_review: int = 0
    new_entities: List[KadiEntity] = field(default_factory=list)


def new_entity_id(entity_type: str) -> str:
    return f"{ENTITY_ID_PREFIX.get(entity_type, 'ENT')}-{uuid.uuid4().hex[:8]}"


def _meta(entity: KadiEntity) -> Dict[str, Any]:
    return dict(entity.meta) if isinstance(entity.meta, dict) else {}


def _mention_record(name: str, value: Optional[str], meta: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": name,
        "value": value,
        "source_file": meta.get("source_file"),
        "source": meta.get("source"),
    }


def entity_aliases(entity: KadiEntity) -> List[str]:
    names = [m.get("name") for m in _meta(entity).get("mentions", []) if isinstance(m, dict)]
    return [n for n in dict.fromkeys(names) if n and n != entity.name]


def _append_mention(target: KadiEntity, name: str, value: Optional[str], meta: Dict[str, Any]) -> None:
    target_meta = _meta(target)
    mentions = list(target_meta.get("mentions") or [])
    if not mentions:
        mentions.append(_mention_record(target.name, target.value, target_meta))
    mentions.append(_mention_record(name, value, meta))
    # Earlier mentions already folded into the merged entity travel with it.
    for earlier in meta.get("mentions") or []:
        if isinstance(earlier, dict) and earlier not in mentions:
            mentions.append(earlier)
    target_meta["mentions"] = mentions
    # JSON columns do not track in-place mutation; reassign so the change is persisted.
    target.meta = target_meta


def _make_entity(mention: MentionInput) -> KadiEntity:
    return KadiEntity(
        id=new_entity_id(mention.entity_type),
        name=mention.name,
        type=mention.entity_type,
        value=mention.value,
        meta=mention.meta,
    )


async def latest_calibration(session: AsyncSession, scope: str) -> Optional[KadiThresholdCalibration]:
    result = await session.execute(
        select(KadiThresholdCalibration)
        .where(KadiThresholdCalibration.scope == scope, KadiThresholdCalibration.status == "CALIBRATED")
        .order_by(KadiThresholdCalibration.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _thresholds_from(row: Optional[KadiThresholdCalibration]) -> ResolutionThresholds:
    if row is None:
        return ResolutionThresholds()
    return ResolutionThresholds(
        merge=row.merge_threshold, ask=row.ask_threshold, source="feedback_calibrated", calibration_id=row.id
    )


async def load_thresholds(session: AsyncSession, entity_type: str) -> ResolutionThresholds:
    """Type-specific calibration if one exists, else the pooled one, else the defaults."""
    for scope in (entity_type, ALL_TYPES_SCOPE):
        row = await latest_calibration(session, scope)
        if row is not None:
            return _thresholds_from(row)
    return ResolutionThresholds()


async def resolve_and_attach(
    session: AsyncSession,
    case: KadiCase,
    mentions: Sequence[MentionInput],
    source: str,
    encoder: Any = _UNSET,
) -> ResolutionSummary:
    """Resolves each mention against the case's entities (and earlier mentions of the same
    batch) and attaches the result to `case`. The caller commits. `case.entities` must be
    loaded."""
    if encoder is _UNSET:
        encoder = get_default_semantic_encoder()

    existing: List[KadiEntity] = list(case.entities)
    summary = ResolutionSummary()
    thresholds_by_type: Dict[str, ResolutionThresholds] = {}

    for mention in mentions:
        if mention.entity_type not in RESOLVABLE_ENTITY_TYPES or not mention.name.strip():
            entity = _make_entity(mention)
            summary.new_entities.append(entity)
            summary.created += 1
            continue

        pool = [e for e in (*existing, *summary.new_entities) if e.type == mention.entity_type and e.name]
        if mention.entity_type not in thresholds_by_type:
            thresholds_by_type[mention.entity_type] = await load_thresholds(session, mention.entity_type)

        decision = resolve_mention(
            EntityMention(name=mention.name[:512], entity_type=mention.entity_type),
            [
                CandidateEntity(id=e.id, name=e.name[:512], entity_type=e.type, aliases=entity_aliases(e))
                for e in pool
            ],
            thresholds=thresholds_by_type[mention.entity_type],
            encoder=encoder,
        )

        target = next((e for e in pool if e.id == decision.matched_candidate_id), None)
        if decision.action == "MERGE" and target is not None:
            _append_mention(target, mention.name, mention.value, mention.meta)
            summary.merged += 1
            if normalize_surface(mention.name) != normalize_surface(target.name):
                session.add(_decision_row(case.id, mention, decision, target, status="auto_merged", source=source))
            continue

        entity = _make_entity(mention)
        summary.new_entities.append(entity)
        summary.created += 1
        if decision.action == "ASK" and target is not None:
            session.add(
                _decision_row(
                    case.id, mention, decision, target, status="pending", source=source, mention_entity_id=entity.id
                )
            )
            summary.pending_review += 1

    case.entities.extend(summary.new_entities)
    session.add_all(summary.new_entities)
    return summary


def _decision_row(case_id, mention, decision, target, *, status, source, mention_entity_id=None):
    return KadiResolutionDecision(
        id=f"RES-{uuid.uuid4().hex[:10]}",
        case_id=case_id,
        entity_type=mention.entity_type,
        action=decision.action,
        status=status,
        source=source,
        mention_entity_id=mention_entity_id,
        candidate_entity_id=target.id,
        candidate_name=target.name,
        mention_payload={"name": mention.name, "value": mention.value, "meta": mention.meta},
        confidence=decision.confidence,
        signals=[s.model_dump() for s in decision.signals],
        reasons=list(decision.reasons),
        thresholds=decision.thresholds.model_dump(),
    )


async def apply_feedback(
    session: AsyncSession, case: KadiCase, decision: KadiResolutionDecision, same_entity: bool
) -> KadiResolutionDecision:
    """Applies a user's answer to a decision. `case.entities` must be loaded."""
    if decision.status not in ("pending", "auto_merged"):
        raise DecisionAlreadyResolved(decision.status)

    by_id = {e.id: e for e in case.entities}
    target = by_id.get(decision.candidate_entity_id)
    if target is None:
        raise DecisionStale("candidate entity no longer exists")

    if decision.status == "pending":
        if same_entity:
            mention = by_id.get(decision.mention_entity_id)
            if mention is None:
                raise DecisionStale("mention entity no longer exists")
            _append_mention(target, mention.name, mention.value, _meta(mention))
            case.entities.remove(mention)
            await session.delete(mention)
            await _supersede_decisions_involving(session, decision, mention.id)
            decision.status = "confirmed"
        else:
            decision.status = "rejected"
    else:
        if same_entity:
            decision.status = "confirmed"
        else:
            payload = decision.mention_payload or {}
            split_meta = dict(payload.get("meta") or {})
            split_meta["split_from"] = target.id
            restored = KadiEntity(
                id=new_entity_id(decision.entity_type),
                name=payload.get("name") or decision.candidate_name,
                type=decision.entity_type,
                value=payload.get("value"),
                meta=split_meta,
            )
            _remove_mention(target, payload)
            case.entities.append(restored)
            session.add(restored)
            decision.mention_entity_id = restored.id
            decision.status = "split"

    decision.feedback_same_entity = same_entity
    decision.feedback_at = datetime.utcnow()
    return decision


def _remove_mention(target: KadiEntity, payload: Dict[str, Any]) -> None:
    meta = _meta(target)
    mentions = list(meta.get("mentions") or [])
    record = _mention_record(payload.get("name"), payload.get("value"), payload.get("meta") or {})
    if record in mentions:
        mentions.remove(record)
    # Only the entity's own original mention left: drop the list entirely.
    meta["mentions"] = mentions if len(mentions) > 1 else []
    if not meta["mentions"]:
        meta.pop("mentions")
    target.meta = meta


async def _supersede_decisions_involving(
    session: AsyncSession, answered: KadiResolutionDecision, removed_entity_id: str
) -> None:
    result = await session.execute(
        select(KadiResolutionDecision).where(
            KadiResolutionDecision.case_id == answered.case_id,
            KadiResolutionDecision.status == "pending",
            KadiResolutionDecision.id != answered.id,
        )
    )
    for other in result.scalars().all():
        if removed_entity_id in (other.mention_entity_id, other.candidate_entity_id):
            other.status = "superseded"


async def recalibrate(session: AsyncSession, entity_type: str) -> List[CalibrationResult]:
    """Recalibrates the pooled thresholds and the ones for `entity_type` from every labeled
    decision, storing one snapshot per scope (INSUFFICIENT_EVIDENCE attempts included)."""
    # The answer just recorded may not be flushed yet (sessions can run with autoflush off);
    # without this the newest label would be missing from its own recalibration.
    await session.flush()
    rows = (
        await session.execute(
            select(
                KadiResolutionDecision.entity_type,
                KadiResolutionDecision.confidence,
                KadiResolutionDecision.feedback_same_entity,
            ).where(KadiResolutionDecision.feedback_same_entity.is_not(None))
        )
    ).all()
    samples = [LabeledOutcome(confidence=c, same_entity=bool(f), entity_type=t) for t, c, f in rows]

    results = []
    for scope, scoped in (
        (ALL_TYPES_SCOPE, samples),
        (entity_type, [s for s in samples if s.entity_type == entity_type]),
    ):
        current = _thresholds_from(await latest_calibration(session, scope))
        result = calibrate_thresholds(scoped, current, scope=scope)
        snapshot = KadiThresholdCalibration(
            id=f"CAL-{uuid.uuid4().hex[:10]}",
            scope=scope,
            status=result.status,
            merge_threshold=result.thresholds.merge,
            ask_threshold=result.thresholds.ask,
            sample_count=len(scoped),
            metrics=result.metrics.model_dump(),
            reasons=list(result.reasons),
        )
        session.add(snapshot)
        await session.flush()
        results.append(result)
    logger.info("Recalibrated entity-resolution thresholds from %d labeled decisions.", len(samples))
    return results
