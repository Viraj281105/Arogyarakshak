"""
SchemeSetu API Endpoints.

Handles government healthcare scheme eligibility checks (PMJAY, MJPJAY).
"""

from datetime import datetime
from typing import Any, List, Literal, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auto_triggers import run_triggers_in_background, upsert_insight
from app.consent import require_case_consent
from app.database import get_db
from app.models import KadiCase, KadiEntity, KadiModuleInsight, SchemeSetuCaseProfile
# Import schemesetu packages
from schemesetu.agent import check_eligibility, EligibilityRequest, SchemeResult
from schemesetu.triggers import IncomeProfile, IncomeTriggerDecision, evaluate_income_trigger
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
    try:
        return await build_case_eligibility(
            case_id,
            income=intake.income,
            location_state=intake.location_state,
            category=intake.category,
            medical_need=intake.medical_need,
            db=db,
        )
    except CaseMedicalNeedMissing:
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


class CaseMedicalNeedMissing(Exception):
    """No medical need was supplied and the case has no diagnosis/procedure entities."""


async def case_medical_need(case_id: str, db: AsyncSession) -> Optional[str]:
    entities_result = await db.execute(
        select(KadiEntity)
        .join(KadiCase.entities)
        .where(KadiCase.id == case_id, KadiEntity.type.in_(["diagnosis", "procedure"]))
    )
    # De-duplicated, order-preserving: a case can carry the same procedure name from more
    # than one source document.
    names = list(dict.fromkeys(e.name for e in entities_result.scalars().all() if e.name))
    return "; ".join(names) if names else None


async def build_case_eligibility(
    case_id: str,
    *,
    income: float,
    location_state: str,
    category: str,
    medical_need: Optional[str],
    db: AsyncSession,
) -> List[SchemeResult]:
    """Shared by the route above and Kadi's auto-triggers (#32, #92). Callers enforce
    consent first."""
    medical_need = medical_need or await case_medical_need(case_id, db)
    if not medical_need:
        raise CaseMedicalNeedMissing()
    return check_eligibility(
        EligibilityRequest(
            income=income, location_state=location_state, category=category, medical_need=medical_need
        )
    )


# --- Consent-bounded income profile & recommendation trigger (#92) ------------

class IncomeProfileRequest(BaseModel):
    annual_income_inr: float = Field(..., ge=0, le=1e10, allow_inf_nan=False, json_schema_extra={"example": 120000.0})
    state: str = Field(..., min_length=2, max_length=64, json_schema_extra={"example": "Maharashtra"})


class IncomeProfileResponse(BaseModel):
    case_id: str
    annual_income_inr: float
    state: str
    trigger: IncomeTriggerDecision
    background_eligibility: Literal["queued", "not_ready", "not_triggered"]
    missing_context: List[str] = Field(default_factory=list)


class StoredIncomeProfile(BaseModel):
    case_id: str
    annual_income_inr: float
    state: str
    updated_at: Any


@router.put("/cases/{case_id}/income-profile", response_model=IncomeProfileResponse)
async def save_income_profile(
    case_id: str,
    body: IncomeProfileRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Saves the case's income profile and, when a scheme newly applies (first profile,
    or a move into a state with its own scheme), queues a background eligibility run (#92).

    Consent-bounded: without the case's stored consent_opt_in nothing is saved (403).
    Only annual income and state are stored. State decides which schemes apply; income is
    recorded but non-determinative, so an income change alone never queues a run.
    """
    await require_case_consent(case_id, db)

    stored = await db.get(SchemeSetuCaseProfile, case_id)
    previous = IncomeProfile(annual_income_inr=stored.annual_income_inr, state=stored.state) if stored else None
    current = IncomeProfile(annual_income_inr=body.annual_income_inr, state=body.state.strip())
    decision = evaluate_income_trigger(current, previous)

    if stored is None:
        stored = SchemeSetuCaseProfile(case_id=case_id)
        db.add(stored)
    stored.annual_income_inr = current.annual_income_inr
    stored.state = current.state
    stored.updated_at = datetime.utcnow()
    await db.commit()

    background = "not_triggered"
    missing: List[str] = []
    if decision.status == "FIRE":
        if await case_medical_need(case_id, db):
            background_tasks.add_task(
                run_triggers_in_background, case_id, "income_profile_updated", ["schemesetu_eligibility"]
            )
            background = "queued"
        else:
            background = "not_ready"
            missing = ["diagnosis or procedure"]
            await upsert_insight(
                db,
                case_id,
                "schemesetu_eligibility",
                status="NOT_READY",
                trigger="income_profile_updated",
                missing_context=missing,
            )
            await db.commit()

    return IncomeProfileResponse(
        case_id=case_id,
        annual_income_inr=current.annual_income_inr,
        state=current.state,
        trigger=decision,
        background_eligibility=background,
        missing_context=missing,
    )


@router.get("/cases/{case_id}/income-profile", response_model=StoredIncomeProfile)
async def get_income_profile(case_id: str, db: AsyncSession = Depends(get_db)):
    await require_case_consent(case_id, db)
    stored = await db.get(SchemeSetuCaseProfile, case_id)
    if stored is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No income profile saved for this case")
    return StoredIncomeProfile(
        case_id=case_id, annual_income_inr=stored.annual_income_inr, state=stored.state, updated_at=stored.updated_at
    )


@router.delete("/cases/{case_id}/income-profile", status_code=status.HTTP_204_NO_CONTENT)
async def delete_income_profile(case_id: str, db: AsyncSession = Depends(get_db)):
    """Withdraws the income profile. The scheme insight derived from it is deleted too."""
    await require_case_consent(case_id, db)
    stored = await db.get(SchemeSetuCaseProfile, case_id)
    if stored is not None:
        await db.delete(stored)
    insight = (
        await db.execute(
            select(KadiModuleInsight).where(
                KadiModuleInsight.case_id == case_id, KadiModuleInsight.module_check == "schemesetu_eligibility"
            )
        )
    ).scalar_one_or_none()
    if insight is not None:
        await db.delete(insight)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    """Projects income from caller-supplied historical data points via linear trend and
    runs the eligibility rules on it (#70). Income is non-determinative for both schemes,
    so the projection cannot change a verdict. ArogyaRakshak has no real historical
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
