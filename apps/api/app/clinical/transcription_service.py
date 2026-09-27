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
    MAX_TASKS_PER_DOCUMENT,
    FieldType,
    MedicineRef,
    ReaderConfidence,
    Reading,
    RiskLevel,
    TaskStatus,
    clean_reading,
    evaluate_consensus,
    merge_ocr_uncertainty,
    normalize_reading,
    plan_ocr_uncertainty,
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
NOT_APPLIED_REASON = (
    "The reading was not applied: it could not be matched to the extracted entry, it named no "
    "drug, or another agreed reading of this entry is still unplaced. The entry is NOT treated as "
    "settled (it will not be price-benchmarked) — confirm it with the dispensing pharmacist."
)
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


def _medicine_ref(m: KadiEntity) -> MedicineRef:
    meta = m.meta if isinstance(m.meta, dict) else {}
    dosage = meta.get("dosage")
    return MedicineRef(m.id, m.name or "", str(dosage) if dosage else None)


async def create_tasks_from_ocr(
    db: AsyncSession,
    case_id: str,
    payloads: Sequence[Dict[str, Any]],
    medicines: Sequence[KadiEntity],
    *,
    document_medicine_ids: Optional[Sequence[str]] = None,
    confident_texts: Sequence[str] = (),
) -> List[KadiTranscriptionTask]:
    """Carries every uncertain OCR reading forward (kadi `plan_ocr_uncertainty`):

    - a reading that names exactly one medicine becomes a human-reading task (at most
      MAX_TASKS_PER_DOCUMENT per document, counted after linking);
    - a reading that names several medicines, only resembles one, lies beyond the cap,
      or names none at all holds the medicine(s) it may concern back as
      `meta.ocr_uncertainty` — so DawaCheck does not benchmark them — until a human
      reads the whole entry. Nothing uncertain silently becomes a trusted fact.

    `medicines` is passed in (the case's in-session entities) because newly resolved
    entities are not flushed yet when this runs inside the upload pipeline."""
    if not payloads:
        return []
    plan = plan_ocr_uncertainty(
        payloads,
        [_medicine_ref(m) for m in medicines],
        document_medicine_ids=document_medicine_ids,
        confident_texts=confident_texts,
        cap=MAX_TASKS_PER_DOCUMENT,
    )
    by_id = {m.id: m for m in medicines}
    for entity_id, held in plan.held_back.items():
        entity = by_id.get(entity_id)
        if entity is None:
            continue
        meta = dict(entity.meta) if isinstance(entity.meta, dict) else {}
        meta["ocr_uncertainty"] = merge_ocr_uncertainty(meta.get("ocr_uncertainty"), held)
        entity.meta = meta
    if plan.held_back or plan.unplaced:
        record_event(
            db,
            event_type=AuditEventType.TRANSCRIPTION_REQUESTED.value,
            subject_type="TRANSCRIPTION",
            subject_id=case_id,
            actor_type=ActorType.SYSTEM.value,
            case_id=case_id,
            details={
                "source": "OCR_LOW_CONFIDENCE",
                "held_back_entities": len(plan.held_back),
                "unplaced_readings": len(plan.unplaced),
            },
        )
    tasks = []
    for p, entity_id in plan.linked:
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
    its name. Returns False when that cannot be done safely: the entity name is left as
    extracted, but the agreed reading is recorded as NOT_APPLIED so consumers keep
    treating the entry as unsettled rather than falling back to the uncertain OCR text."""
    meta = dict(entity.meta) if isinstance(entity.meta, dict) else {}
    previous = meta.get("human_transcription") or {}
    # A whole-entry reading (a case-holder flag of the entry, or an OCR reading that was
    # the entire entry) is the only thing that can settle an entry held back as
    # NOT_APPLIED or `ocr_uncertainty`; a later partial reading must not erase either and
    # mark the entry settled while the unplaced part may still contradict it.
    whole_entry = task.source == "CASE_HOLDER_FLAGGED" or (
        normalize_reading(task.ocr_candidate or "") == normalize_reading(entity.name or "")
    )
    if previous.get("status") == "NOT_APPLIED" and not whole_entry:
        return False
    if whole_entry:
        resolved_name = substitute_reading(entity.name or "", entity.name or "", task.final_value or "")
    else:
        base_name = (previous.get("value") if previous.get("status") == "RESOLVED" else None) or entity.name
        resolved_name = substitute_reading(base_name or "", task.ocr_candidate or "", task.final_value or "")
    record = {
        "task_id": task.id,
        "field_type": task.field_type,
        "whole_entry": whole_entry,
        "replaced_reading": task.ocr_candidate,
        "human_reading": task.final_value,
        "provenance": ProvenanceClass.HUMAN_REVIEWED.value,
        "independent_readings": task.required_reviews,
        # Who read it matters: transcription readers are not prescribers.
        "reader_roles": reader_roles,
        "resolved_at": task.resolved_at.isoformat() if task.resolved_at else None,
    }
    if resolved_name is None:
        meta["human_transcription"] = {**record, "status": "NOT_APPLIED"}
        entity.meta = meta
        return False
    meta["human_transcription"] = {**record, "status": "RESOLVED", "value": resolved_name}
    uncertainty = meta.get("ocr_uncertainty")
    if whole_entry and isinstance(uncertainty, dict) and uncertainty.get("status") == "UNRESOLVED":
        meta["ocr_uncertainty"] = {**uncertainty, "status": "SETTLED_BY_HUMAN_READING", "settled_by_task_id": task.id}
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
            task.resolution_reason = f"{result.reason} {NOT_APPLIED_REASON}"
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
        # RESOLVED only says the readers agreed; whether the agreed reading was placed
        # into the entry (APPLIED) or held back as unsettled (NOT_APPLIED) is separate.
        "outcome": (
            None
            if task.status != TaskStatus.RESOLVED.value
            else ("NOT_APPLIED" if NOT_APPLIED_REASON in (task.resolution_reason or "") else "APPLIED")
        ),
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
    # Deterministic when an entry has several unresolved tasks: an OPEN one (still
    # awaiting readers) is reported first; otherwise the MOST RECENT escalation, so only
    # a whole-entry reading settled after every escalation can clear the entry.
    def rank(t: KadiTranscriptionTask):
        if t.status in OPEN_TASK_STATES:
            return (1, t.created_at or datetime.min, t.id)
        return (0, t.resolved_at or t.created_at or datetime.min, t.id)

    out: Dict[str, KadiTranscriptionTask] = {}
    for t in rows.scalars().all():
        current = out.get(t.entity_id)
        if current is None or rank(t) > rank(current):
            out[t.entity_id] = t
    return out
