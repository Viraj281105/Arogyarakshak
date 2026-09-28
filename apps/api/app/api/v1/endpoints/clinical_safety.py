"""
Kadi — Clinical Safety Governance endpoints (ADR-011). Mounted under /api/v1/kadi.

Public: the ACTIVE rules and their full version history (transparency).
Board members (doctors seated by the operator): propose, submit, approve, activate,
version and retire rules — every step attributable.
Case holder: the escalations active rules raise for their case. Not consent-gated: a
safety signal must never be hidden behind the cross-module sharing opt-in, and it uses
only Kadi's own case context.
"""

from datetime import date
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kadi.clinical_review import SAFETY_FLOOR_DISCLAIMER

from app.case_auth import require_case_access
from app.clinical import safety_service
from app.clinical.audit import events_for_subject
from app.clinical.auth import require_board_member
from app.clinical.context import evaluate_case_safety_or_unavailable
from app.database import get_db
from app.models import KadiCase, KadiClinicalReviewer, KadiSafetyRule

router = APIRouter()

PUBLIC_RULE_STATES = ("ACTIVE", "SUPERSEDED", "RETIRED")


class RuleWrite(BaseModel):
    rule_key: Optional[str] = Field(None, max_length=61)
    title: str = Field(..., max_length=160)
    description: str = Field(..., max_length=2000)
    trigger: Dict[str, Any]
    action: Dict[str, Any]
    source_name: str = Field(..., max_length=300)
    source_reference: Optional[str] = Field(None, max_length=500)
    source_version: Optional[str] = Field(None, max_length=120)
    source_section: Optional[str] = Field(None, max_length=200)
    limitations: str = Field(..., max_length=2000)
    effective_date: Optional[date] = None
    review_due_date: date
    changelog: Optional[str] = Field(None, max_length=2000)


class RuleDecision(BaseModel):
    decision: Literal["APPROVE", "REJECT"]
    comment: Optional[str] = Field(None, max_length=1000)


class RetireRequest(BaseModel):
    reason: str = Field(..., max_length=1000)


def _envelope(rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"rules": rules, "disclaimer": SAFETY_FLOOR_DISCLAIMER}


@router.get("/safety-rules")
async def list_public_rules(
    rule_status: Literal["ACTIVE", "SUPERSEDED", "RETIRED", "ALL_PUBLIC"] = Query("ACTIVE", alias="status"),
    db: AsyncSession = Depends(get_db),
):
    states = PUBLIC_RULE_STATES if rule_status == "ALL_PUBLIC" else (rule_status,)
    rows = await db.execute(
        select(KadiSafetyRule).where(KadiSafetyRule.status.in_(states)).order_by(KadiSafetyRule.rule_key, KadiSafetyRule.version)
    )
    return _envelope([await safety_service.rule_view(db, r) for r in rows.scalars().all()])


@router.get("/safety-rules/workspace")
async def board_workspace(board: KadiClinicalReviewer = Depends(require_board_member), db: AsyncSession = Depends(get_db)):
    """Every rule in every state, for board members."""
    rows = await db.execute(select(KadiSafetyRule).order_by(KadiSafetyRule.rule_key, KadiSafetyRule.version))
    return _envelope([await safety_service.rule_view(db, r) for r in rows.scalars().all()])


@router.get("/safety-rules/{rule_id}")
async def get_public_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    rule = await safety_service.get_rule(db, rule_id)
    if rule.status not in PUBLIC_RULE_STATES:
        raise HTTPException(status_code=404, detail="Safety rule not found.")
    return await safety_service.rule_view(db, rule)


@router.get("/safety-rules/{rule_id}/versions")
async def rule_versions(rule_id: str, db: AsyncSession = Depends(get_db)):
    rule = await safety_service.get_rule(db, rule_id)
    rows = await db.execute(
        select(KadiSafetyRule)
        .where(KadiSafetyRule.rule_key == rule.rule_key, KadiSafetyRule.status.in_(PUBLIC_RULE_STATES))
        .order_by(KadiSafetyRule.version)
    )
    return _envelope([await safety_service.rule_view(db, r) for r in rows.scalars().all()])


@router.get("/safety-rules/{rule_id}/audit")
async def rule_audit(rule_id: str, db: AsyncSession = Depends(get_db)):
    await safety_service.get_rule(db, rule_id)
    return await events_for_subject(db, rule_id)


@router.post("/safety-rules", status_code=status.HTTP_201_CREATED)
async def propose_rule(req: RuleWrite, board: KadiClinicalReviewer = Depends(require_board_member), db: AsyncSession = Depends(get_db)):
    rule = await safety_service.create_rule(db, board, req.model_dump())
    await db.commit()
    return await safety_service.rule_view(db, rule)


@router.put("/safety-rules/{rule_id}")
async def edit_rule(rule_id: str, req: RuleWrite, board: KadiClinicalReviewer = Depends(require_board_member), db: AsyncSession = Depends(get_db)):
    rule = await safety_service.get_rule(db, rule_id)
    await safety_service.update_rule(db, board, rule, req.model_dump())
    await db.commit()
    return await safety_service.rule_view(db, rule)


@router.post("/safety-rules/{rule_id}/submit")
async def submit_rule(rule_id: str, board: KadiClinicalReviewer = Depends(require_board_member), db: AsyncSession = Depends(get_db)):
    rule = await safety_service.get_rule(db, rule_id)
    await safety_service.submit_rule(db, board, rule)
    await db.commit()
    return await safety_service.rule_view(db, rule)


@router.post("/safety-rules/{rule_id}/decisions")
async def decide_rule(rule_id: str, req: RuleDecision, board: KadiClinicalReviewer = Depends(require_board_member), db: AsyncSession = Depends(get_db)):
    rule = await safety_service.get_rule(db, rule_id)
    await safety_service.decide_rule(db, board, rule, req.decision, req.comment)
    await db.commit()
    return await safety_service.rule_view(db, rule)


@router.post("/safety-rules/{rule_id}/activate")
async def activate_rule(rule_id: str, board: KadiClinicalReviewer = Depends(require_board_member), db: AsyncSession = Depends(get_db)):
    rule = await safety_service.get_rule(db, rule_id)
    await safety_service.activate_rule(db, board, rule)
    await db.commit()
    return await safety_service.rule_view(db, rule)


@router.post("/safety-rules/{rule_id}/retire")
async def retire_rule(rule_id: str, req: RetireRequest, board: KadiClinicalReviewer = Depends(require_board_member), db: AsyncSession = Depends(get_db)):
    rule = await safety_service.get_rule(db, rule_id)
    await safety_service.retire_rule(db, board, rule, req.reason)
    await db.commit()
    return await safety_service.rule_view(db, rule)


@router.post("/safety-rules/{rule_id}/new-version", status_code=status.HTTP_201_CREATED)
async def new_rule_version(rule_id: str, board: KadiClinicalReviewer = Depends(require_board_member), db: AsyncSession = Depends(get_db)):
    rule = await safety_service.get_rule(db, rule_id)
    draft = await safety_service.new_version(db, board, rule)
    await db.commit()
    return await safety_service.rule_view(db, draft)


@router.get("/cases/{case_id}/safety-escalations")
async def case_safety_escalations(case_id: str, case: KadiCase = Depends(require_case_access), db: AsyncSession = Depends(get_db)):
    """Escalations from ACTIVE rules. `status` is EVALUATED, or UNAVAILABLE when the rules
    could not be evaluated — clients must render that as "Safety check unavailable", never
    as "no escalation" or "no rules active"."""
    return await evaluate_case_safety_or_unavailable(db, case_id)
