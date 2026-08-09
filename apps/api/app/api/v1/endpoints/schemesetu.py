"""
SchemeSetu API Endpoints.

Handles government healthcare scheme eligibility checks (PMJAY, MJPJAY).
"""

from typing import List
from fastapi import APIRouter, status
from pydantic import BaseModel, Field

# Import schemesetu packages
from schemesetu.agent import check_eligibility, EligibilityRequest, SchemeResult

router = APIRouter()


# --- Pydantic Schemas ---------------------------------------------------------
class IntakeEligibilityRequest(BaseModel):
    income: float = Field(..., description="Annual family income in INR", example=120000.0)
    location_state: str = Field(..., description="State of residence", example="Maharashtra")
    category: str = Field(default="General", description="Social category", example="OBC")
    medical_need: str = Field(..., description="Medical procedure or diagnosis", example="Heart bypass")


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
