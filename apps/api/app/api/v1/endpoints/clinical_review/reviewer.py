"""Reviewer routes (X-Reviewer-Token): assigned queue, accept/decline, evidence, and the
statement and fact-confirmation lifecycle. Every write carrying professional attribution
requires this credential, which no model output ever holds."""


from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from kadi.clinical_review.lifecycle import (
    FACT_DECISION_CONFIRMATION_TEXT,
    FINALIZATION_CONFIRMATION_TEXT,
)

from app.clinical import service
from app.clinical.audit import events_for_review
from app.clinical.auth import (
    require_reviewer,
)
from app.clinical.serializers import (
    fact_view,
    reviewer_review_summary,
    statement_view,
)
from app.database import get_db
from app.models import KadiClinicalReviewer

router = APIRouter()
from app.api.v1.endpoints.clinical_review.schemas import AcceptRequest, ConfirmRequest, DeclineRequest, FactDecisionRequest, StatementWrite, WithdrawRequest


# --- Reviewer routes -----------------------------------------------------------

@router.get("/clinical-reviews/assigned")
async def my_assigned_reviews(reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)):
    return [
        {**reviewer_review_summary(r, reviewer), "coi_context": r.coi_context}
        for r in await service.reviewer_queue(db, reviewer)
    ]


@router.get("/clinical-reviews/{review_id}")
async def reviewer_review_detail(
    review_id: str, reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)
):
    review = await service.reviewer_review(db, reviewer, review_id, need_evidence_access=False)
    own = [s for s in await service.statements_for_review(db, review.id) if s.reviewer_id == reviewer.id]
    return {
        **reviewer_review_summary(review, reviewer),
        "coi_context": review.coi_context,
        "statements": [statement_view(s, include_draft_fields=True) for s in own],
        "facts": [fact_view(f) for f in await service.facts_for_review(db, review.id)],
        "finalization_confirmation_text": FINALIZATION_CONFIRMATION_TEXT,
        "fact_decision_confirmation_text": FACT_DECISION_CONFIRMATION_TEXT,
    }


@router.post("/clinical-reviews/{review_id}/accept")
async def accept_review(
    review_id: str,
    req: AcceptRequest,
    reviewer: KadiClinicalReviewer = Depends(require_reviewer),
    db: AsyncSession = Depends(get_db),
):
    review = await service.reviewer_review(db, reviewer, review_id, need_evidence_access=False)
    await service.accept_review(db, reviewer, review, req.coi_category, req.coi_disclosure)
    await db.commit()
    return reviewer_review_summary(review, reviewer)


@router.post("/clinical-reviews/{review_id}/decline")
async def decline_review(
    review_id: str,
    req: DeclineRequest,
    reviewer: KadiClinicalReviewer = Depends(require_reviewer),
    db: AsyncSession = Depends(get_db),
):
    review = await service.reviewer_review(db, reviewer, review_id, need_evidence_access=False)
    await service.decline_review(db, reviewer, review, req.reason)
    await db.commit()
    return {"review_id": review.id, "status": review.status}


@router.get("/clinical-reviews/{review_id}/evidence")
async def review_evidence(
    review_id: str, reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)
):
    review = await service.reviewer_review(db, reviewer, review_id, need_evidence_access=True)
    payload = service.evidence_for_reviewer(db, reviewer, review)
    await db.commit()
    return payload


async def _reviewer_in_review(db, reviewer, review_id):
    return await service.reviewer_review(db, reviewer, review_id, need_evidence_access=True)


@router.post("/clinical-reviews/{review_id}/statements", status_code=status.HTTP_201_CREATED)
async def create_statement(
    review_id: str,
    req: StatementWrite,
    reviewer: KadiClinicalReviewer = Depends(require_reviewer),
    db: AsyncSession = Depends(get_db),
):
    review = await _reviewer_in_review(db, reviewer, review_id)
    stmt = await service.create_statement(
        db, reviewer, review,
        evidence_reviewed=req.evidence_reviewed, reviewer_statement=req.reviewer_statement, limitations=req.limitations,
    )
    await db.commit()
    return statement_view(stmt, include_draft_fields=True)


@router.put("/clinical-reviews/{review_id}/statements/{statement_id}")
async def update_statement(
    review_id: str,
    statement_id: str,
    req: StatementWrite,
    reviewer: KadiClinicalReviewer = Depends(require_reviewer),
    db: AsyncSession = Depends(get_db),
):
    review = await _reviewer_in_review(db, reviewer, review_id)
    stmt = await service.update_statement(
        db, reviewer, review, statement_id,
        evidence_reviewed=req.evidence_reviewed, reviewer_statement=req.reviewer_statement, limitations=req.limitations,
    )
    await db.commit()
    return statement_view(stmt, include_draft_fields=True)


@router.post("/clinical-reviews/{review_id}/statements/{statement_id}/submit")
async def submit_statement(review_id: str, statement_id: str, reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)):
    review = await _reviewer_in_review(db, reviewer, review_id)
    stmt = await service.submit_statement(db, reviewer, review, statement_id)
    await db.commit()
    return statement_view(stmt, include_draft_fields=True)


@router.post("/clinical-reviews/{review_id}/statements/{statement_id}/return-to-draft")
async def return_statement_to_draft(review_id: str, statement_id: str, reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)):
    review = await _reviewer_in_review(db, reviewer, review_id)
    stmt = await service.return_to_draft(db, reviewer, review, statement_id)
    await db.commit()
    return statement_view(stmt, include_draft_fields=True)


@router.post("/clinical-reviews/{review_id}/statements/{statement_id}/finalize")
async def finalize_statement(
    review_id: str,
    statement_id: str,
    req: ConfirmRequest,
    reviewer: KadiClinicalReviewer = Depends(require_reviewer),
    db: AsyncSession = Depends(get_db),
):
    """Requires the reviewer's own credential AND the exact confirmation sentence. There is
    no server-side path that supplies either on the reviewer's behalf."""
    review = await _reviewer_in_review(db, reviewer, review_id)
    stmt = await service.finalize_statement(
        db, reviewer, review, statement_id, confirmation=req.confirmation, confirmation_text=req.confirmation_text
    )
    await db.commit()
    return statement_view(stmt)


@router.post("/clinical-reviews/{review_id}/statements/{statement_id}/revise", status_code=status.HTTP_201_CREATED)
async def revise_statement(review_id: str, statement_id: str, reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)):
    review = await _reviewer_in_review(db, reviewer, review_id)
    draft = await service.revise_statement(db, reviewer, review, statement_id)
    await db.commit()
    return statement_view(draft, include_draft_fields=True)


@router.post("/clinical-reviews/{review_id}/statements/{statement_id}/withdraw")
async def withdraw_statement(
    review_id: str,
    statement_id: str,
    req: WithdrawRequest,
    reviewer: KadiClinicalReviewer = Depends(require_reviewer),
    db: AsyncSession = Depends(get_db),
):
    review = await _reviewer_in_review(db, reviewer, review_id)
    stmt = await service.withdraw_statement(db, reviewer, review, statement_id, req.reason)
    await db.commit()
    return statement_view(stmt)


@router.post("/clinical-reviews/{review_id}/facts/{fact_id}/decision")
async def decide_fact(
    review_id: str,
    fact_id: str,
    req: FactDecisionRequest,
    reviewer: KadiClinicalReviewer = Depends(require_reviewer),
    db: AsyncSession = Depends(get_db),
):
    review = await _reviewer_in_review(db, reviewer, review_id)
    fact = await service.decide_fact(
        db, reviewer, review, fact_id,
        decision=req.decision, note=req.note, confirmation=req.confirmation, confirmation_text=req.confirmation_text,
    )
    await db.commit()
    return fact_view(fact)


@router.get("/clinical-reviews/{review_id}/audit")
async def reviewer_review_audit(review_id: str, reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)):
    review = await service.reviewer_review(db, reviewer, review_id, need_evidence_access=False)
    return await events_for_review(db, review.id)
