"""Gathers the persisted records behind a case timeline (kadi.timeline builds it).

Read-only. Sources: stored document digests (never the documents), the append-only
clinical audit trail, module insights, safety scan matches, the appeal/claim rows and the
in-memory processing status. Plus the CURRENT trust state of the case's medicines, which
is reported as "now", not as a past event.
"""

from collections import Counter
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clinical.transcription_service import open_tasks_by_entity
from app.models import (
    BillNyayAppeal,
    DaaviSetuClaim,
    KadiCase,
    KadiCaseDocument,
    KadiClinicalAuditEvent,
    KadiEntity,
    KadiModuleInsight,
    KadiSafetyRule,
    KadiSafetyScanResult,
)
from kadi.clinical_review.medicine_trust import PendingTask, decide_medicine_trust
from kadi.timeline import TimelineInput, build_case_timeline


async def case_timeline(db: AsyncSession, case_id: str, live_status: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    docs = (
        await db.execute(select(KadiCaseDocument).where(KadiCaseDocument.case_id == case_id))
    ).scalars().all()
    entities = (
        await db.execute(select(KadiEntity).join(KadiCase.entities).where(KadiCase.id == case_id))
    ).scalars().all()
    audit = (
        await db.execute(
            select(KadiClinicalAuditEvent)
            .where(KadiClinicalAuditEvent.case_id == case_id)
            .order_by(KadiClinicalAuditEvent.created_at)
        )
    ).scalars().all()
    insights = (
        await db.execute(select(KadiModuleInsight).where(KadiModuleInsight.case_id == case_id))
    ).scalars().all()
    scans = (
        await db.execute(select(KadiSafetyScanResult).where(KadiSafetyScanResult.case_id == case_id))
    ).scalars().all()
    rule_titles: Dict[str, str] = {}
    if scans:
        rows = await db.execute(select(KadiSafetyRule.id, KadiSafetyRule.title).where(KadiSafetyRule.id.in_({s.rule_id for s in scans})))
        rule_titles = {rid: title for rid, title in rows.all()}
    appeal = (await db.execute(select(BillNyayAppeal.created_at).where(BillNyayAppeal.case_id == case_id))).scalar_one_or_none()
    claim = (await db.execute(select(DaaviSetuClaim.created_at).where(DaaviSetuClaim.case_id == case_id))).scalar_one_or_none()

    counts = Counter(e.type for e in entities)
    medicines = [e for e in entities if e.type == "medicine"]
    pending = await open_tasks_by_entity(db, case_id)
    trust = Counter()
    for m in medicines:
        task = pending.get(m.id)
        decision = decide_medicine_trust(
            m.name or "",
            m.meta if isinstance(m.meta, dict) else {},
            PendingTask(task_id=task.id, status=task.status, resolved_at=task.resolved_at.isoformat() if task.resolved_at else None)
            if task is not None
            else None,
        )
        trust["checkable" if decision.benchmarkable else "held_back"] += 1
        if decision.name_provenance == "HUMAN_REVIEWED":
            trust["human_reviewed"] += 1
    held_back_at_upload = sum(
        1 for m in medicines if isinstance(m.meta, dict) and (m.meta.get("ocr_uncertainty") or {}).get("status")
    )

    timeline = build_case_timeline(
        TimelineInput(
            documents=[{"at": d.created_at, "extension": d.extension, "source": d.source} for d in docs if d.created_at],
            entity_counts=dict(counts),
            held_back_medicines=held_back_at_upload,
            audit_events=[
                {"at": a.created_at, "event_type": a.event_type, "actor_type": a.actor_type, "details": a.details or {}}
                for a in audit
                if a.created_at
            ],
            module_insights=[
                {"at": i.updated_at or i.created_at, "module_check": i.module_check, "status": i.status, "summary": i.summary or {}}
                for i in insights
                if (i.updated_at or i.created_at)
            ],
            safety_matches=[{"at": s.created_at, "rule_title": rule_titles.get(s.rule_id)} for s in scans if s.created_at],
            appeal_at=appeal,
            claim_package_at=claim,
            live_status=live_status,
        )
    )
    timeline["now"] = {
        "medicines": len(medicines),
        "medicines_checkable": trust["checkable"],
        "medicines_held_back": trust["held_back"],
        "medicines_human_reviewed": trust["human_reviewed"],
    }
    return timeline
