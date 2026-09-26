"""
Human OCR resolution service (ADR-011). Reviewers here are "transcription reviewers" —
pharmacists, medical transcriptionists, trained annotators (or doctors) — never
presented as doctors by virtue of this task.

Blindness: a reviewer never sees another reviewer's reading, and for HIGH-risk
(possible medication) fields never sees the OCR guess either, so two agreeing readings
are genuinely independent.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kadi.clinical_review import ActorType, AuditEventType, ProvenanceClass
from kadi.clinical_review.transcription import (
    MASK,
    OPEN_TASK_STATES,
    FieldType,
    ReaderConfidence,
    Reading,
    RiskLevel,
    TaskStatus,
    clean_reading,
    evaluate_consensus,
    link_candidate_to_entity,
    required_reviews_for,
    risk_for_field,
    substitute_reading,
)
from kadi.redaction import redact_pii

from app.clinical.audit import record_event
from app.clinical.auth import reviewer_available
from app.clinical.serializers import category_label
from app.consent import require_case_consent
from app.models import (
    KadiCase,
    KadiClinicalReviewer,
    KadiEntity,
    KadiTranscriptionAssignment,
    KadiTranscriptionSubmission,
    KadiTranscriptionTask,
)

NOT_FOUND = "Transcription task not found."
REVIEWER_INSTRUCTIONS = (
    "Read the original document held by the patient (ArogyaRakshak does not store document "
    "images). Type exactly what is written in the masked position. If you cannot read it "
    "with confidence, mark it unreadable — never guess."
)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _audit(db, task: KadiTranscriptionTask, event: AuditEventType, actor_type: str, actor_id=None, details=None):
    record_event(
        db,
        event_type=event.value,
        subject_type="TRANSCRIPTION",
        subject_id=task.id,
        actor_type=actor_type,
        actor_id=actor_id,
        case_id=task.case_id,
        details={"field_type": task.field_type, "risk_level": task.risk_level, **(details or {})},
    )


async def create_tasks_from_ocr(
    db: AsyncSession,
    case_id: str,
    payloads: Sequence[Dict[str, Any]],
    medicines: Sequence[KadiEntity],
) -> List[KadiTranscriptionTask]:
    """Creates a task only for an uncertain reading that links, token for token, to one
    extracted medicine — the only readings anything downstream (DawaCheck) consumes.
    Everything else is dropped rather than turned into human work that goes nowhere.

    `medicines` is passed in (the case's in-session entities) because newly resolved
    entities are not flushed yet when this runs inside the upload pipeline."""
    if not payloads:
        return []
    named = [(m.id, m.name or "") for m in medicines]
    tasks = []
    for p in payloads:
        entity_id = link_candidate_to_entity(p.get("ocr_candidate") or "", named)
        if entity_id is None:
            continue
        task = KadiTranscriptionTask(
            id=_new_id("TR"),
            case_id=case_id,
            entity_id=entity_id,
            source="OCR_LOW_CONFIDENCE",
            field_type=p["field_type"],
            risk_level=p["risk_level"],
            required_reviews=p["required_reviews"],
            ocr_candidate=p.get("ocr_candidate"),
            ocr_confidence=p.get("ocr_confidence"),
            masked_context=p["masked_context"],
            location_hint=p.get("location_hint"),
            status=TaskStatus.OPEN.value,
        )
        db.add(task)
        _audit(db, task, AuditEventType.TRANSCRIPTION_REQUESTED, ActorType.SYSTEM.value,
               details={"source": "OCR_LOW_CONFIDENCE", "linked_to_entity": bool(task.entity_id)})
        tasks.append(task)
    return tasks


async def flag_entity(db: AsyncSession, case: KadiCase, entity_id: str, field_type: str) -> KadiTranscriptionTask:
    """A case holder flags a whole extracted medicine entry as possibly misread; readers
    transcribe the full entry as written. Partial-field flags are refused: a reading of
    one field could not be applied to the entry without guessing where it belongs."""
    if field_type != FieldType.MEDICINE_NAME.value:
        raise HTTPException(
            status_code=422,
            detail="Only a whole medicine entry (field_type MEDICINE_NAME) can be flagged for human reading.",
        )
    ftype = field_type
    row = await db.execute(
        select(KadiEntity).join(KadiCase.entities).where(KadiCase.id == case.id, KadiEntity.id == entity_id)
    )
    entity = row.scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found in this case.")
    existing = await db.execute(
        select(KadiTranscriptionTask).where(
            KadiTranscriptionTask.case_id == case.id,
            KadiTranscriptionTask.entity_id == entity_id,
            KadiTranscriptionTask.field_type == ftype,
            KadiTranscriptionTask.status.in_(list(OPEN_TASK_STATES)),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="An open transcription task already exists for this field.")
    risk = risk_for_field(ftype)
    meta = entity.meta if isinstance(entity.meta, dict) else {}
    context_bits = [f"{entity.type}: {MASK}"]
    if meta.get("dosage") and ftype != FieldType.STRENGTH.value:
        context_bits.append(f"dosage {meta['dosage']}")
    task = KadiTranscriptionTask(
        id=_new_id("TR"),
        case_id=case.id,
        entity_id=entity.id,
        source="CASE_HOLDER_FLAGGED",
        field_type=ftype,
        risk_level=risk.value,
        required_reviews=required_reviews_for(risk.value),
        ocr_candidate=redact_pii(entity.name or "")[:200] or None,
        ocr_confidence=None,
        masked_context=redact_pii(" · ".join(context_bits))[:500],
        location_hint=None,
        status=TaskStatus.OPEN.value,
    )
    db.add(task)
    _audit(db, task, AuditEventType.TRANSCRIPTION_REQUESTED, ActorType.CASE_HOLDER.value,
           details={"source": "CASE_HOLDER_FLAGGED"})
    return task


async def list_case_tasks(db: AsyncSession, case_id: str) -> List[KadiTranscriptionTask]:
    rows = await db.execute(
        select(KadiTranscriptionTask)
        .where(KadiTranscriptionTask.case_id == case_id)
        .order_by(KadiTranscriptionTask.created_at)
    )
    return list(rows.scalars().all())


async def get_case_task(db: AsyncSession, case_id: str, task_id: str) -> KadiTranscriptionTask:
    task = await db.get(KadiTranscriptionTask, task_id)
    if task is None or task.case_id != case_id:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return task


async def _assignments(db, task_id: str) -> List[KadiTranscriptionAssignment]:
    rows = await db.execute(select(KadiTranscriptionAssignment).where(KadiTranscriptionAssignment.task_id == task_id))
    return list(rows.scalars().all())


async def _submissions(db, task_id: str) -> List[KadiTranscriptionSubmission]:
    rows = await db.execute(
        select(KadiTranscriptionSubmission)
        .where(KadiTranscriptionSubmission.task_id == task_id)
        .order_by(KadiTranscriptionSubmission.created_at)
    )
    return list(rows.scalars().all())


async def assign_task(
    db: AsyncSession, case: KadiCase, task: KadiTranscriptionTask, reviewer_id: str, share_with_reviewer_consent: bool
) -> KadiClinicalReviewer:
    require_case_consent(case)
    if share_with_reviewer_consent is not True:
        raise HTTPException(
            status_code=422,
            detail="Sharing this reading with a human reviewer needs share_with_reviewer_consent set to true.",
        )
    if task.status not in OPEN_TASK_STATES:
        raise HTTPException(status_code=409, detail=f"Task is {task.status}; it can no longer be assigned.")
    reviewer = await db.get(KadiClinicalReviewer, reviewer_id)
    if not reviewer_available(reviewer):
        raise HTTPException(status_code=404, detail="Reviewer not found.")
    if any(a.reviewer_id == reviewer_id for a in await _assignments(db, task.id)):
        raise HTTPException(status_code=409, detail="This reviewer is already assigned to the task.")
    db.add(KadiTranscriptionAssignment(id=_new_id("TRA"), task_id=task.id, case_id=task.case_id, reviewer_id=reviewer.id))
    task.consent_confirmed_at = task.consent_confirmed_at or datetime.utcnow()
    _audit(db, task, AuditEventType.TRANSCRIPTION_ASSIGNED, ActorType.CASE_HOLDER.value,
           details={"reviewer_id": reviewer.id, "reviewer_category": reviewer.category})
    return reviewer


async def cancel_task(db: AsyncSession, task: KadiTranscriptionTask) -> None:
    if task.status == TaskStatus.CANCELLED.value:
        return
    task.status = TaskStatus.CANCELLED.value
    _audit(db, task, AuditEventType.TRANSCRIPTION_CANCELLED, ActorType.CASE_HOLDER.value)


async def reviewer_task(db: AsyncSession, reviewer: KadiClinicalReviewer, task_id: str) -> KadiTranscriptionTask:
    task = await db.get(KadiTranscriptionTask, task_id)
    if task is None or task.status == TaskStatus.CANCELLED.value:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    if not any(a.reviewer_id == reviewer.id for a in await _assignments(db, task.id)):
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    case = await db.get(KadiCase, task.case_id)
    if case is None or not case.consent_opt_in:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return task


async def reviewer_queue(db: AsyncSession, reviewer: KadiClinicalReviewer) -> List[KadiTranscriptionTask]:
    rows = await db.execute(
        select(KadiTranscriptionTask)
        .join(KadiTranscriptionAssignment, KadiTranscriptionAssignment.task_id == KadiTranscriptionTask.id)
        .where(
            KadiTranscriptionAssignment.reviewer_id == reviewer.id,
            KadiTranscriptionTask.status != TaskStatus.CANCELLED.value,
        )
        .order_by(KadiTranscriptionTask.created_at)
    )
    return list(rows.scalars().all())


async def reviewer_task_view(db: AsyncSession, reviewer: KadiClinicalReviewer, task: KadiTranscriptionTask) -> Dict[str, Any]:
    mine = next((s for s in await _submissions(db, task.id) if s.reviewer_id == reviewer.id), None)
    show_candidate = task.risk_level == RiskLevel.STANDARD.value
    return {
        "task_id": task.id,
        "field_type": task.field_type,
        "risk_level": task.risk_level,
        "masked_context": task.masked_context,
        "location_hint": task.location_hint,
        # HIGH-risk readings are blind to the OCR guess to avoid anchoring.
        "ocr_candidate": task.ocr_candidate if show_candidate else None,
        "ocr_candidate_hidden": not show_candidate,
        "accepting_readings": task.status in OPEN_TASK_STATES and mine is None,
        "your_reading": (
            {"value": mine.value, "unreadable": mine.unreadable, "reviewer_confidence": mine.reviewer_confidence, "submitted_at": mine.created_at}
            if mine else None
        ),
        "instructions": REVIEWER_INSTRUCTIONS,
    }


def _entity_meta_update(entity: KadiEntity, task: KadiTranscriptionTask, reader_roles: List[str]) -> bool:
    """Records the human reading on the entity by substituting only the uncertain part of
    its name. Returns False (entity untouched) when that cannot be done safely."""
    meta = dict(entity.meta) if isinstance(entity.meta, dict) else {}
    base_name = (meta.get("human_transcription") or {}).get("value") or entity.name
    resolved_name = substitute_reading(base_name or "", task.ocr_candidate or "", task.final_value or "")
    if resolved_name is None:
        return False
    meta["human_transcription"] = {
        "task_id": task.id,
        "field_type": task.field_type,
        "status": "RESOLVED",
        "value": resolved_name,
        "replaced_reading": task.ocr_candidate,
        "human_reading": task.final_value,
        "provenance": ProvenanceClass.HUMAN_REVIEWED.value,
        "independent_readings": task.required_reviews,
        # Who read it matters: transcription readers are not prescribers.
        "reader_roles": reader_roles,
        "resolved_at": task.resolved_at.isoformat() if task.resolved_at else None,
    }
    entity.meta = meta
    return True


async def submit_reading(
    db: AsyncSession,
    reviewer: KadiClinicalReviewer,
    task: KadiTranscriptionTask,
    *,
    value: Optional[str],
    unreadable: bool,
    reviewer_confidence: str,
    notes: Optional[str],
) -> KadiTranscriptionTask:
    if task.status not in OPEN_TASK_STATES:
        raise HTTPException(status_code=409, detail=f"Task is {task.status}; it is no longer accepting readings.")
    existing = await _submissions(db, task.id)
    if any(s.reviewer_id == reviewer.id for s in existing):
        raise HTTPException(status_code=409, detail="You have already submitted a reading for this task.")
    try:
        confidence = ReaderConfidence(reviewer_confidence).value
        clean_value = clean_reading(value)
        clean_notes = clean_reading(notes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not unreadable and not clean_value:
        raise HTTPException(status_code=422, detail="Provide the text you read, or mark it unreadable.")

    submission = KadiTranscriptionSubmission(
        id=_new_id("TRS"),
        task_id=task.id,
        case_id=task.case_id,
        reviewer_id=reviewer.id,
        value=None if unreadable else clean_value,
        unreadable=bool(unreadable),
        reviewer_confidence=confidence,
        notes=clean_notes,
    )
    db.add(submission)
    _audit(db, task, AuditEventType.TRANSCRIPTION_SUBMITTED, ActorType.REVIEWER.value, reviewer.id,
           {"unreadable": bool(unreadable), "reviewer_confidence": confidence})

    readings = [Reading(s.reviewer_id, s.value, s.unreadable, s.reviewer_confidence) for s in existing + [submission]]
    result = evaluate_consensus(task.risk_level, readings)
    task.status = result.status.value
    task.resolution_reason = result.reason
    if result.status == TaskStatus.RESOLVED:
        task.final_value = result.final_value
        task.resolved_at = datetime.utcnow()
        applied = False
        if task.entity_id:
            entity = await db.get(KadiEntity, task.entity_id)
            if entity is not None:
                roles = []
                for s in existing + [submission]:
                    r = await db.get(KadiClinicalReviewer, s.reviewer_id)
                    roles.append(category_label(r.category) if r else "Reader")
                applied = _entity_meta_update(entity, task, roles)
        if task.entity_id and not applied:
            task.resolution_reason = (
                f"{result.reason} The reading could not be matched to the extracted entry, so the "
                "entry was left unchanged — confirm it with the dispensing pharmacist."
            )
        _audit(db, task, AuditEventType.TRANSCRIPTION_CONFIRMED, ActorType.SYSTEM.value,
               details={"independent_readings": len({r.reviewer_id for r in readings}), "applied_to_entity": applied})
    elif result.status == TaskStatus.HUMAN_ESCALATION_REQUIRED:
        task.resolved_at = datetime.utcnow()
        _audit(db, task, AuditEventType.TRANSCRIPTION_REJECTED, ActorType.SYSTEM.value,
               details={"reason": "disagreement_or_unreadable"})
    return task


async def case_task_view(db: AsyncSession, task: KadiTranscriptionTask) -> Dict[str, Any]:
    submissions = await _submissions(db, task.id)
    assignments = await _assignments(db, task.id)
    closed = task.status in (TaskStatus.RESOLVED.value, TaskStatus.HUMAN_ESCALATION_REQUIRED.value)
    readings = []
    if closed:
        for s in submissions:
            reviewer = await db.get(KadiClinicalReviewer, s.reviewer_id)
            readings.append(
                {
                    "value": s.value,
                    "unreadable": s.unreadable,
                    "reviewer_confidence": s.reviewer_confidence,
                    "reviewer_name": reviewer.name if reviewer else None,
                    "reviewer_role": category_label(reviewer.category) if reviewer else None,
                    "submitted_at": s.created_at,
                }
            )
    return {
        "task_id": task.id,
        "entity_id": task.entity_id,
        "source": task.source,
        "field_type": task.field_type,
        "risk_level": task.risk_level,
        "required_reviews": task.required_reviews,
        "ocr_candidate": task.ocr_candidate,
        "ocr_confidence": task.ocr_confidence,
        "masked_context": task.masked_context,
        "status": task.status,
        "resolution_reason": task.resolution_reason,
        "final_value": task.final_value,
        "final_value_provenance": ProvenanceClass.HUMAN_REVIEWED.value if task.final_value else None,
        "readings_received": len(submissions),
        "assigned_reviewer_count": len(assignments),
        "readings": readings,
        "created_at": task.created_at,
        "resolved_at": task.resolved_at,
    }


async def open_tasks_by_entity(db: AsyncSession, case_id: str) -> Dict[str, KadiTranscriptionTask]:
    """Unresolved possibly-medication tasks per linked entity — DawaCheck must not treat
    those entities as settled medication facts."""
    rows = await db.execute(
        select(KadiTranscriptionTask).where(
            KadiTranscriptionTask.case_id == case_id,
            KadiTranscriptionTask.entity_id.is_not(None),
            KadiTranscriptionTask.risk_level == RiskLevel.HIGH.value,
            KadiTranscriptionTask.status.in_(list(OPEN_TASK_STATES) + [TaskStatus.HUMAN_ESCALATION_REQUIRED.value]),
        )
    )
    return {t.entity_id: t for t in rows.scalars().all()}
