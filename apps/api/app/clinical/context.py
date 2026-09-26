"""
Case context helpers shared by the clinical-review layer and module endpoints (ADR-011).

Machine-derived signals (plausibility, safety escalations) are computed here once so a
module route and the review service can never disagree about them.
"""

from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from billnyay.plausibility import EvidenceRef, PlausibilityAssessment, assess_clinical_plausibility
from kadi.clinical_review import SAFETY_FLOOR_DISCLAIMER
from kadi.clinical_review.evidence import EntityRecord
from kadi.clinical_review.safety import ActiveRule, evaluate_rules

from app.models import KadiCase, KadiEntity, KadiSafetyRule

NO_ACTIVE_RULES_NOTE = (
    "No clinical safety rules are active on this deployment. The absence of an escalation "
    "is therefore not a safety assessment of any kind."
)


async def load_entity_records(db: AsyncSession, case_id: str) -> List[EntityRecord]:
    rows = await db.execute(
        select(KadiEntity).join(KadiCase.entities).where(KadiCase.id == case_id)
    )
    return [
        EntityRecord(
            id=e.id,
            type=e.type,
            name=e.name or "",
            value=e.value,
            meta=e.meta if isinstance(e.meta, dict) else {},
        )
        for e in rows.scalars().all()
    ]


def safety_context(entities: Sequence[EntityRecord]) -> List[Tuple[str, str]]:
    context: List[Tuple[str, str]] = []
    for e in entities:
        if e.type == "document_text":
            context.append((e.type, e.value or ""))
        elif e.type in ("diagnosis", "procedure", "medicine"):
            context.append((e.type, e.name))
    return context


def _active_rule(row: KadiSafetyRule) -> ActiveRule:
    return ActiveRule(
        rule_id=row.id,
        rule_key=row.rule_key,
        version=row.version,
        title=row.title,
        trigger=row.trigger,
        action=row.action,
        source_name=row.source_name,
        source_version=row.source_version,
        source_section=row.source_section,
        limitations=row.limitations,
        effective_date=row.effective_date,
        review_due_date=row.review_due_date,
    )


async def load_active_rules(db: AsyncSession) -> List[ActiveRule]:
    rows = await db.execute(select(KadiSafetyRule).where(KadiSafetyRule.status == "ACTIVE"))
    return [_active_rule(r) for r in rows.scalars().all()]


async def evaluate_case_safety(
    db: AsyncSession, case_id: str, entities: Optional[Sequence[EntityRecord]] = None
) -> Dict[str, Any]:
    entities = entities if entities is not None else await load_entity_records(db, case_id)
    rules = await load_active_rules(db)
    escalations = evaluate_rules(rules, safety_context(entities), today=date.today())
    return {
        "case_id": case_id,
        "active_rule_count": len(rules),
        "escalations": escalations,
        "disclaimer": SAFETY_FLOOR_DISCLAIMER,
        "coverage_note": NO_ACTIVE_RULES_NOTE if not rules else (
            f"{len(rules)} active rule(s) were checked. They cover specific red flags only; "
            "no escalation does not mean the case is clinically safe."
        ),
    }


def _refs(entities: Sequence[EntityRecord], entity_type: str) -> List[EvidenceRef]:
    return [
        EvidenceRef(item_id=e.id, kind=e.type, value=e.name, provenance="AI_DERIVED")
        for e in entities
        if e.type == entity_type and e.name
    ]


async def assess_case_plausibility(
    db: AsyncSession, case_id: str, entities: Optional[Sequence[EntityRecord]] = None
) -> Tuple[PlausibilityAssessment, Dict[str, Any]]:
    entities = entities if entities is not None else await load_entity_records(db, case_id)
    safety = await evaluate_case_safety(db, case_id, entities)
    assessment = assess_clinical_plausibility(
        _refs(entities, "diagnosis"),
        _refs(entities, "procedure"),
        safety_escalations=len(safety["escalations"]),
    )
    return assessment, safety
