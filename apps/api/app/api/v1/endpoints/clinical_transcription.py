"""
Kadi — Human OCR resolution endpoints (ADR-011). Mounted under /api/v1/kadi.

Case holder: list/flag/assign/cancel transcription tasks for their case.
Transcription reviewer: see a blind task view and submit one independent reading.
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.case_auth import require_case_access
from app.clinical import transcription_service as ts
from app.clinical.auth import require_reviewer
from app.database import get_db
from app.models import KadiCase, KadiClinicalReviewer

router = APIRouter()


class FlagRequest(BaseModel):
    entity_id: str = Field(..., max_length=60)
    field_type: str = Field("MEDICINE_NAME", max_length=20)


class TranscriptionAssign(BaseModel):
    reviewer_id: str = Field(..., max_length=40)
    share_with_reviewer_consent: bool = False


class ReadingRequest(BaseModel):
    value: Optional[str] = Field(None, max_length=200)
    unreadable: bool = False
    reviewer_confidence: Literal["HIGH", "MEDIUM", "LOW"] = "HIGH"
    notes: Optional[str] = Field(None, max_length=200)


@router.get("/cases/{case_id}/transcriptions")
async def list_transcriptions(case_id: str, case: KadiCase = Depends(require_case_access), db: AsyncSession = Depends(get_db)):
    return [await ts.case_task_view(db, t) for t in await ts.list_case_tasks(db, case_id)]


@router.post("/cases/{case_id}/transcriptions", status_code=status.HTTP_201_CREATED)
async def flag_for_transcription(
    case_id: str, req: FlagRequest, case: KadiCase = Depends(require_case_access), db: AsyncSession = Depends(get_db)
):
    """The case holder marks an extracted value as possibly misread (e.g. a medicine name
    that looks wrong). Possible-medication fields always need two agreeing readings."""
    task = await ts.flag_entity(db, case, req.entity_id, req.field_type)
    await db.commit()
    return await ts.case_task_view(db, task)


@router.post("/cases/{case_id}/transcriptions/{task_id}/assign")
async def assign_transcription(
    case_id: str,
    task_id: str,
    req: TranscriptionAssign,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    task = await ts.get_case_task(db, case_id, task_id)
    await ts.assign_task(db, case, task, req.reviewer_id, req.share_with_reviewer_consent)
    await db.commit()
    return await ts.case_task_view(db, task)


@router.post("/cases/{case_id}/transcriptions/{task_id}/cancel")
async def cancel_transcription(
    case_id: str, task_id: str, case: KadiCase = Depends(require_case_access), db: AsyncSession = Depends(get_db)
):
    task = await ts.get_case_task(db, case_id, task_id)
    await ts.cancel_task(db, task)
    await db.commit()
    return await ts.case_task_view(db, task)


@router.get("/transcriptions/assigned")
async def my_transcriptions(reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)):
    return [await ts.reviewer_task_view(db, reviewer, t) for t in await ts.reviewer_queue(db, reviewer)]


@router.get("/transcriptions/{task_id}")
async def transcription_detail(task_id: str, reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)):
    task = await ts.reviewer_task(db, reviewer, task_id)
    return await ts.reviewer_task_view(db, reviewer, task)


@router.post("/transcriptions/{task_id}/readings", status_code=status.HTTP_201_CREATED)
async def submit_transcription_reading(
    task_id: str,
    req: ReadingRequest,
    reviewer: KadiClinicalReviewer = Depends(require_reviewer),
    db: AsyncSession = Depends(get_db),
):
    task = await ts.reviewer_task(db, reviewer, task_id)
    await ts.submit_reading(
        db, reviewer, task,
        value=req.value, unreadable=req.unreadable, reviewer_confidence=req.reviewer_confidence, notes=req.notes,
    )
    await db.commit()
    return await ts.reviewer_task_view(db, reviewer, task)
