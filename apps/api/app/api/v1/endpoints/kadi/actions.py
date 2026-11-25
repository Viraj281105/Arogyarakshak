"""Action and resolution records (ADR-031): what the user chose to do about a finding, and
what they say happened. Mounted under /api/v1/kadi. Owner only; nothing is sent anywhere."""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from kadi.resolution_tracking import ActionKind, ActionModule, ActionStatus, ContactMethod, TrackingError

from app.case_auth import require_case_access
from app.database import get_db
from app.models import KadiCase
from app.services import case_actions

router = APIRouter()

NOT_FOUND_DETAIL = "Action not found in this case."
_AMOUNT = Field(None, ge=0, le=1_000_000_000, description="Rupees, as recorded by the user. Not verified.")


class ActionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module: ActionModule
    kind: ActionKind
    title: str = Field(..., min_length=1, max_length=200)
    finding_ref: Optional[str] = Field(None, max_length=200, description="Which finding this answers.")
    institution: Optional[str] = Field(None, max_length=200)
    contact_method: Optional[ContactMethod] = None
    next_step: Optional[str] = Field(None, max_length=500)
    amount_disputed: Optional[float] = _AMOUNT


class ActionEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ActionStatus
    occurred_on: Optional[date] = Field(None, description="The day it happened, as the user remembers it.")
    note: Optional[str] = Field(None, max_length=1000)
    evidence_sha256: Optional[str] = Field(None, pattern=r"^[0-9a-f]{64}$", description="A document already in this case.")
    institution: Optional[str] = Field(None, max_length=200)
    contact_method: Optional[ContactMethod] = None
    next_step: Optional[str] = Field(None, max_length=500)
    amount_disputed: Optional[float] = _AMOUNT
    amount_corrected: Optional[float] = _AMOUNT


class ActionEvent(BaseModel):
    status: ActionStatus
    occurred_on: Optional[date]
    note: Optional[str]
    evidence_sha256: Optional[str]
    provenance: str = Field(..., description="'user_recorded': entered by the user, not independently verified.")
    recorded_at: datetime


class CaseAction(BaseModel):
    id: str
    module: ActionModule
    kind: ActionKind
    title: str
    finding_ref: Optional[str]
    status: ActionStatus
    allowed_next: List[ActionStatus]
    institution: Optional[str]
    contact_method: Optional[ContactMethod]
    next_step: Optional[str]
    amount_disputed: Optional[float]
    amount_corrected: Optional[float]
    created_at: datetime
    updated_at: datetime
    events: List[ActionEvent]


class CaseActionList(BaseModel):
    actions: List[CaseAction]


def _refused(exc: TrackingError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/cases/{case_id}/actions", response_model=CaseActionList)
async def list_case_actions(
    case_id: str, case: KadiCase = Depends(require_case_access), db: AsyncSession = Depends(get_db)
):
    """Every tracked action of the case with its history, oldest first."""
    return {"actions": await case_actions.list_actions(db, case.id)}


@router.post("/cases/{case_id}/actions", response_model=CaseAction, status_code=status.HTTP_201_CREATED)
async def create_case_action(
    case_id: str,
    req: ActionCreate,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Starts tracking a next step. It is 'planned' until the user records more."""
    try:
        return await case_actions.create_action(db, case.id, req.model_dump(mode="json"))
    except TrackingError as exc:
        raise _refused(exc)


@router.post("/cases/{case_id}/actions/{action_id}/events", response_model=CaseAction)
async def record_case_action_event(
    case_id: str,
    action_id: str,
    req: ActionEventCreate,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Records what the user says happened. Refused (409) when it could not be true, for
    example a response to something never sent."""
    fields = req.model_dump(mode="json")
    fields["occurred_on"] = req.occurred_on
    try:
        return await case_actions.record_event(db, case.id, action_id, fields)
    except case_actions.ActionNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL)
    except TrackingError as exc:
        raise _refused(exc)


@router.delete("/cases/{case_id}/actions/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case_action(
    case_id: str,
    action_id: str,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    try:
        await case_actions.delete_action(db, case.id, action_id)
    except case_actions.ActionNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
