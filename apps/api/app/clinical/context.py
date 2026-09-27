"""
Case context helpers shared by the clinical-review layer and module endpoints (ADR-011).

Machine-derived signals (plausibility, safety escalations) are computed here once so a
module route and the review service can never disagree about them.
"""

import logging
import uuid
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from billnyay.plausibility import EvidenceRef, PlausibilityAssessment, assess_clinical_plausibility
from kadi.clinical_review import SAFETY_FLOOR_DISCLAIMER
from kadi.clinical_review.evidence import EntityRecord
from kadi.clinical_review.safety import (
    ActiveRule,
    carried_forward_terms,
    escalation_for,
    evaluate_rules,
    scan_full_text,
    sort_escalations,
)

from app.models import KadiCase, KadiEntity, KadiSafetyRule, KadiSafetyScanResult

logger = logging.getLogger("arogyarakshak.clinical.context")

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


SCAN_SCOPE_NOTE = (
    "Each uploaded document was checked in full against the rules active when it was "
    "uploaded (a term found then still counts under a newer version of the same rule that "
    "still lists it). Rules or terms activated later are checked only against the extracted "
    "diagnoses, procedures and medicines and the first 1,000 characters of each document "
    "(the redacted excerpt ArogyaRakshak keeps)."
)


async def scan_document_for_safety(db: AsyncSession, case_id: str, full_text: str) -> int:
    """Upload-time full-text scan (the document is still in transient memory). Persists
    only rule id/version and matched terms. Returns the number of rules matched."""
    rules = await load_active_rules(db)
    if not rules or not full_text:
        return 0
    matches = scan_full_text(rules, full_text, today=date.today())
    for m in matches:
        db.add(
            KadiSafetyScanResult(
                id=f"SSR-{uuid.uuid4().hex[:12]}",
                case_id=case_id,
                rule_id=m["rule_id"],
                rule_version=m["rule_version"],
                matched_terms=m["matched_terms"],
            )
        )
    return len(matches)


async def evaluate_case_safety(
    db: AsyncSession, case_id: str, entities: Optional[Sequence[EntityRecord]] = None
) -> Dict[str, Any]:
    entities = entities if entities is not None else await load_entity_records(db, case_id)
    rules = await load_active_rules(db)
    escalations = evaluate_rules(rules, safety_context(entities), today=date.today())

    # Merge red flags found in the full text at upload time, for rules still ACTIVE — or
    # for the ACTIVE successor of a superseded version, when it still lists the term.
    by_rule = {e["rule_id"]: e for e in escalations}
    active = {r.rule_id: r for r in rules}
    active_by_key = {r.rule_key: r for r in rules}
    scans = (await db.execute(select(KadiSafetyScanResult).where(KadiSafetyScanResult.case_id == case_id))).scalars().all()
    stale_ids = {s.rule_id for s in scans if s.rule_id not in active}
    stale_keys: Dict[str, str] = {}
    if stale_ids:
        rows = await db.execute(select(KadiSafetyRule.id, KadiSafetyRule.rule_key).where(KadiSafetyRule.id.in_(stale_ids)))
        stale_keys = {rid: key for rid, key in rows.all()}
    for scan in scans:
        rule = active.get(scan.rule_id)
        terms = list(scan.matched_terms or [])
        if rule is None:
            rule = active_by_key.get(stale_keys.get(scan.rule_id, ""))
            terms = carried_forward_terms(rule, terms) if rule is not None else []
            if not terms:
                continue
        if rule.rule_id in by_rule:
            merged = by_rule[rule.rule_id]["matched_terms"] + terms
            by_rule[rule.rule_id]["matched_terms"] = list(dict.fromkeys(merged))
        else:
            by_rule[rule.rule_id] = escalation_for(rule, terms, date.today())

    return {
        "case_id": case_id,
        "status": "EVALUATED",
        "active_rule_count": len(rules),
        "escalations": sort_escalations(list(by_rule.values())),
        "disclaimer": SAFETY_FLOOR_DISCLAIMER,
        "scope_note": SCAN_SCOPE_NOTE,
        "coverage_note": NO_ACTIVE_RULES_NOTE if not rules else (
            f"{len(rules)} active rule(s) were checked. They cover specific red flags only; "
            "no escalation does not mean the case is clinically safe. " + SCAN_SCOPE_NOTE
        ),
    }


def _refs(entities: Sequence[EntityRecord], entity_type: str) -> List[EvidenceRef]:
    return [
        EvidenceRef(item_id=e.id, kind=e.type, value=e.name, provenance="AI_DERIVED")
        for e in entities
        if e.type == entity_type and e.name
    ]


SAFETY_UNAVAILABLE_NOTE = (
    "Safety check unavailable: the clinical safety rules could not be evaluated for this case. "
    "No safety assessment has been made — this is not the same as \"no escalation\"."
)


def safety_unavailable(case_id: str) -> Dict[str, Any]:
    """What a caller gets when the safety evaluation itself failed. It must never look
    like an evaluation that found nothing (or like "no rules are active")."""
    return {
        "case_id": case_id,
        "status": "UNAVAILABLE",
        "active_rule_count": None,
        "escalations": [],
        "disclaimer": SAFETY_FLOOR_DISCLAIMER,
        "scope_note": None,
        "coverage_note": SAFETY_UNAVAILABLE_NOTE,
    }


async def evaluate_case_safety_or_unavailable(
    db: AsyncSession, case_id: str, entities: Optional[Sequence[EntityRecord]] = None
) -> Dict[str, Any]:
    """`evaluate_case_safety`, isolated in a SAVEPOINT so a failure is reported as
    UNAVAILABLE without poisoning the caller's transaction."""
    try:
        async with db.begin_nested():
            return await evaluate_case_safety(db, case_id, entities)
    except Exception:  # noqa: BLE001 — any failure must surface as UNAVAILABLE, never as "safe"
        logger.exception("Clinical safety evaluation failed for case %s", case_id)
        return safety_unavailable(case_id)


async def assess_case_plausibility(
    db: AsyncSession, case_id: str, entities: Optional[Sequence[EntityRecord]] = None
) -> Tuple[PlausibilityAssessment, Dict[str, Any]]:
    entities = entities if entities is not None else await load_entity_records(db, case_id)
    safety = await evaluate_case_safety_or_unavailable(db, case_id, entities)
    assessment = assess_clinical_plausibility(
        _refs(entities, "diagnosis"),
        _refs(entities, "procedure"),
        safety_escalations=len(safety["escalations"]),
        safety_check_available=safety.get("status") != "UNAVAILABLE",
    )
    return assessment, safety
