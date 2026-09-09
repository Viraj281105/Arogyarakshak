"""
BimaNyay API Endpoints.

Handles health insurance denial audits, statutory clause analysis,
and multi-tier IRDAI grievance timeline tracking.
"""

import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import BimaNyayCase, BimaNyayGrievance, BimaNyayTimelineEvent
from bimanyay import (
    ClaimDenialInput,
    DisputeAuditResult,
    GrievanceTrackerResponse,
    analyze_insurance_denial,
    calculate_grievance_timeline,
)

logger = logging.getLogger("arogyarakshak.api.bimanyay")
router = APIRouter()


class TimelineRequest(BaseModel):
    insurer_name: str = Field(..., description="Insurance company name")
    date_initiated: str = Field(..., description="Date grievance initiated (YYYY-MM-DD)")
    claim_number: Optional[str] = Field(None, description="Insurance claim reference number")
    current_tier: str = Field(default="LEVEL_1_GRO", description="Current escalation tier")


@router.post("/analyze", response_model=DisputeAuditResult, status_code=status.HTTP_200_OK)
async def analyze_denial(
    req: ClaimDenialInput,
    db: AsyncSession = Depends(get_db)
):
    """
    Audits an insurance claim repudiation or deduction against IRDAI regulations.
    Generates 3-tier appeal documents: GRO, IRDAI Bima Bharosa, and Ombudsman.
    """
    try:
        result = analyze_insurance_denial(req)

        # Persist audit record in database
        case_id = str(uuid.uuid4())
        case_record = BimaNyayCase(
            id=case_id,
            policy_number=req.policy_number,
            insurer_name=req.insurer_name,
            policy_age_years=req.policy_age_years,
            claimed_amount=req.claimed_amount,
            denied_amount=req.denied_or_deducted_amount,
            denial_category=req.denial_category,
            denial_reason_raw=req.denial_reason_raw,
            diagnosis=req.diagnosis,
            is_wrongful=result.is_wrongful_denial,
            reversal_probability=result.reversal_probability_score,
            primary_grounds=result.primary_dispute_grounds,
        )
        db.add(case_record)
        await db.commit()

        return result
    except Exception as e:
        logger.error(f"Error analyzing claim denial: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze claim denial: {str(e)}")


@router.post("/timeline", response_model=GrievanceTrackerResponse, status_code=status.HTTP_200_OK)
async def track_timeline(
    req: TimelineRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Calculates statutory milestone deadlines and SLA tracking for dispute escalation.
    """
    try:
        timeline = calculate_grievance_timeline(
            insurer_name=req.insurer_name,
            date_initiated=req.date_initiated,
            claim_number=req.claim_number,
            current_tier=req.current_tier,
        )

        # Persist grievance record
        grievance_id = str(uuid.uuid4())
        grievance_record = BimaNyayGrievance(
            id=grievance_id,
            claim_number=req.claim_number,
            insurer_name=req.insurer_name,
            current_tier=req.current_tier,
            date_initiated=req.date_initiated,
        )
        db.add(grievance_record)

        for event in timeline.timeline_events:
            event_record = BimaNyayTimelineEvent(
                id=str(uuid.uuid4()),
                grievance_id=grievance_id,
                tier=event.tier,
                title=event.title,
                deadline_date=event.deadline_date,
                status=event.status,
                instructions=event.instructions,
            )
            db.add(event_record)

        await db.commit()
        return timeline
    except Exception as e:
        logger.error(f"Error tracking grievance timeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to calculate grievance timeline: {str(e)}")
