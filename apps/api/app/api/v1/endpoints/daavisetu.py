"""
DaaviSetu API Endpoints.

Handles claim and pre-authorization document generation.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import KadiCase, KadiEntity
# Import daavisetu packages
from daavisetu.generator import generate_claim_package, ClaimData, ClaimPackage

logger = logging.getLogger("arogyarakshak.api.daavisetu")
router = APIRouter()


# --- Pydantic Schemas ---------------------------------------------------------
class PreAuthFormRequest(BaseModel):
    policy_number: str = Field(..., description="Insurance policy ID", json_schema_extra={"example": "POL77654"})
    patient_name: str = Field(..., description="Full name of the patient", json_schema_extra={"example": "Viraj Jadhao"})



# --- Route Implementations ----------------------------------------------------

@router.post("/cases/{case_id}/claim", response_model=ClaimPackage, status_code=status.HTTP_200_OK)
async def generate_pre_auth_form(
    case_id: str,
    req: PreAuthFormRequest,
    db: AsyncSession = Depends(get_db)
):
    """Pre-populates a cashless pre-authorization form based on case entities."""
    # 1. Fetch case
    result = await db.execute(select(KadiCase).where(KadiCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # 2. Gather procedure/hospital entities (fallback to generic defaults if not present)
    entities_result = await db.execute(
        select(KadiEntity).join(KadiCase.entities).where(KadiCase.id == case_id)
    )
    entities = entities_result.scalars().all()
    
    hospital = "General Hospital"
    diagnosis = "Discharged Patient Medical Recovery"
    treatment = "General clinical medical observation"
    
    for entity in entities:
        if entity.type == "hospital":
            hospital = entity.name
        elif entity.type == "procedure":
            treatment = entity.name
        elif entity.type == "diagnosis":
            diagnosis = entity.name

    # 3. Create input and execute daavisetu claim generation
    claim_input = ClaimData(
        policy_number=req.policy_number,
        patient_name=req.patient_name,
        hospital_name=hospital,
        diagnosis=diagnosis,
        estimated_cost=case.total_charged,
        treatment_plan=treatment,
    )
    
    package = generate_claim_package(case_id=case_id, claim_input=claim_input)
    return package
