"""
SchemeSetu API Endpoints.

Handles government healthcare scheme eligibility checks (PMJAY, MJPJAY).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.consent import require_case_consent
from app.database import get_db
from app.models import KadiCase, KadiEntity
# Import schemesetu packages
from schemesetu.agent import check_eligibility, EligibilityRequest, SchemeResult
from schemesetu.reasoning_agent import reason_about_eligibility, EligibilityReasoning
from schemesetu.trend_estimator import (
    project_future_eligibility,
    EligibilityTrendResult,
    IncomeDataPoint,
)
from schemesetu.transition_adviser import advise_transition, TransitionAdvice

router = APIRouter()


# --- Pydantic Schemas ---------------------------------------------------------
class IntakeEligibilityRequest(BaseModel):
    income: float = Field(..., description="Annual family income in INR", json_schema_extra={"example": 120000.0})
    location_state: str = Field(..., description="State of residence", json_schema_extra={"example": "Maharashtra"})
    category: str = Field(default="General", description="Social category", json_schema_extra={"example": "OBC"})
    medical_need: str = Field(..., description="Medical procedure or diagnosis", json_schema_extra={"example": "Heart bypass"})


class CaseIntakeEligibilityRequest(BaseModel):
    """Intake for /cases/{case_id}/eligibility (#23).

    income, location_state and category are never derivable from a hospital bill, so
    they remain required, direct user input. Only medical_need may be omitted — it is
    then resolved from the case's Kadi-extracted diagnosis/procedure entities.
    """

    income: float = Field(..., description="Annual family income in INR", json_schema_extra={"example": 120000.0})
    location_state: str = Field(..., description="State of residence", json_schema_extra={"example": "Maharashtra"})
    category: str = Field(default="General", description="Social category", json_schema_extra={"example": "OBC"})
    medical_need: Optional[str] = Field(
        None,
        description="Medical procedure or diagnosis. When omitted, resolved from the "
        "case's diagnosis/procedure entities as extracted by Kadi from BillNyay/"
        "DawaCheck uploads.",
    )



# --- Route Implementations ----------------------------------------------------

@router.post("/eligibility", response_model=List[SchemeResult], status_code=status.HTTP_200_OK)
async def check_scheme_eligibility(intake: IntakeEligibilityRequest):
    """Checks estimated government healthcare scheme eligibility based on intake variables."""
    # Convert api pydantic request to package pydantic request
    req = EligibilityRequest(
        income=intake.income,
        location_state=intake.location_state,
        category=intake.category,
        medical_need=intake.medical_need,
    )

    results = check_eligibility(req)
    return results


@router.post(
    "/cases/{case_id}/eligibility", response_model=List[SchemeResult], status_code=status.HTTP_200_OK
)
async def check_case_scheme_eligibility(
    case_id: str, intake: CaseIntakeEligibilityRequest, db: AsyncSession = Depends(get_db)
):
    """Checks scheme eligibility using context Kadi extracted for this case (#23).

    This route reads cross-module case context (diagnosis/procedure entities), unlike
    the request-body-only /eligibility route above, so it requires the case's
    consent_opt_in (see app.consent) before returning anything.
    """
    await require_case_consent(case_id, db)

    medical_need = intake.medical_need
    if not medical_need:
        entities_result = await db.execute(
            select(KadiEntity)
            .join(KadiCase.entities)
            .where(KadiCase.id == case_id, KadiEntity.type.in_(["diagnosis", "procedure"]))
        )
        # De-duplicated, order-preserving: a case can carry the same procedure name
        # from both OCR line items and LLM extraction.
        names = list(dict.fromkeys(e.name for e in entities_result.scalars().all() if e.name))
        medical_need = "; ".join(names) if names else None

    if not medical_need:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": (
                    "medical_need was not supplied and no diagnosis or procedure was "
                    "extracted for this case. Provide it explicitly — eligibility "
                    "cannot be assessed against nothing."
                ),
            },
        )

    req = EligibilityRequest(
        income=intake.income,
        location_state=intake.location_state,
        category=intake.category,
        medical_need=medical_need,
    )
    return check_eligibility(req)


@router.post("/eligibility/reasoning", response_model=EligibilityReasoning, status_code=status.HTTP_200_OK)
async def eligibility_reasoning(intake: IntakeEligibilityRequest):
    """Returns the same eligibility verdict as /eligibility, plus a step-by-step
    reasoning trace of which criteria were checked and why (#21). See
    schemesetu.reasoning_agent for why this is an explainable rules index, not
    retrieval-augmented generation over a vector store."""
    req = EligibilityRequest(
        income=intake.income,
        location_state=intake.location_state,
        category=intake.category,
        medical_need=intake.medical_need,
    )
    return reason_about_eligibility(req)


class TrendEligibilityRequest(BaseModel):
    income_history: List[IncomeDataPoint] = Field(
        ..., min_length=2, description="At least 2 historical (year, annual_income) data points"
    )
    target_year: int = Field(..., description="Calendar year to project eligibility for")
    location_state: str
    category: str = "General"
    medical_need: str = "Not specified"


@router.post("/eligibility/trend", response_model=EligibilityTrendResult, status_code=status.HTTP_200_OK)
async def eligibility_trend(intake: TrendEligibilityRequest):
    """Projects future PMJAY/MJPJAY eligibility from caller-supplied historical income
    data points via linear trend (#70). ArogyaRakshak has no real historical
    demographic dataset of its own — see schemesetu.trend_estimator — so this only
    projects a trend from data the caller actually provides."""
    try:
        return project_future_eligibility(
            income_history=intake.income_history,
            target_year=intake.target_year,
            location_state=intake.location_state,
            category=intake.category,
            medical_need=intake.medical_need,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


class TransitionEligibilityRequest(BaseModel):
    previous: IntakeEligibilityRequest
    current: IntakeEligibilityRequest


@router.post("/eligibility/transition", response_model=TransitionAdvice, status_code=status.HTTP_200_OK)
async def eligibility_transition(intake: TransitionEligibilityRequest):
    """Generates a transition checklist when eligibility moves between PMJAY and
    MJPJAY across two intakes (#71) — e.g. before/after relocating to/from Maharashtra."""
    previous_req = EligibilityRequest(
        income=intake.previous.income,
        location_state=intake.previous.location_state,
        category=intake.previous.category,
        medical_need=intake.previous.medical_need,
    )
    current_req = EligibilityRequest(
        income=intake.current.income,
        location_state=intake.current.location_state,
        category=intake.current.category,
        medical_need=intake.current.medical_need,
    )
    return advise_transition(previous_req, current_req)
