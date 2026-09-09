"""
DaaviSetu API Endpoints.

Handles claim and pre-authorization document generation.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import KadiCase, KadiEntity
# Import daavisetu packages
from daavisetu.generator import generate_claim_package, generate_preauth_pdf, ClaimData, ClaimPackage

logger = logging.getLogger("arogyarakshak.api.daavisetu")
router = APIRouter()


# --- Pydantic Schemas ---------------------------------------------------------
class PreAuthFormRequest(BaseModel):
    policy_number: str = Field(..., description="Insurance policy ID", json_schema_extra={"example": "POL77654"})
    patient_name: str = Field(..., description="Full name of the patient", json_schema_extra={"example": "Viraj Jadhao"})
    hospital_name: Optional[str] = Field(None, description="Network hospital name", json_schema_extra={"example": "Apollo Hospital"})
    diagnosis: Optional[str] = Field(None, description="Clinical diagnosis or ICD-10 code", json_schema_extra={"example": "Appendicitis"})
    treatment_plan: Optional[str] = Field(None, description="Proposed surgical/medical procedure", json_schema_extra={"example": "Laparoscopic Appendectomy"})



# --- Route Implementations ----------------------------------------------------

@router.post("/cases/{case_id}/claim", response_model=ClaimPackage, status_code=status.HTTP_200_OK)
async def generate_pre_auth_form(
    case_id: str,
    req: PreAuthFormRequest,
    db: AsyncSession = Depends(get_db)
):
    """Pre-populates a cashless pre-authorization form based on user input and case entities."""
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
    
    hospital = req.hospital_name
    diagnosis = req.diagnosis
    treatment = req.treatment_plan

    for entity in entities:
        if not hospital and entity.type == "hospital":
            hospital = entity.name
        elif not treatment and entity.type == "procedure":
            treatment = entity.name
        elif not diagnosis and entity.type == "diagnosis":
            diagnosis = entity.name

    hospital = hospital or "General Hospital"
    diagnosis = diagnosis or "Discharged Patient Medical Recovery"
    treatment = treatment or "General clinical medical observation"

    # 3. Create input and execute daavisetu claim generation
    claim_input = ClaimData(
        policy_number=req.policy_number,
        patient_name=req.patient_name,
        hospital_name=hospital,
        diagnosis=diagnosis,
        estimated_cost=case.total_charged if case.total_charged > 0 else 45000.0,
        treatment_plan=treatment,
    )
    
    package = generate_claim_package(case_id=case_id, claim_input=claim_input)
    return package


@router.get("/cases/{case_id}/claim/pdf")
async def download_preauth_pdf(case_id: str, db: AsyncSession = Depends(get_db)):
    """Downloads the compiled IRDAI Standard Pre-Authorization Form (Annexure-B) PDF."""
    result = await db.execute(select(KadiCase).where(KadiCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    entities_result = await db.execute(
        select(KadiEntity).join(KadiCase.entities).where(KadiCase.id == case_id)
    )
    entities = entities_result.scalars().all()

    hospital = "General Hospital"
    diagnosis = "Discharged Patient Medical Recovery"
    treatment = "General clinical medical observation"
    patient = "Patient"

    for entity in entities:
        if entity.type == "hospital":
            hospital = entity.name
        elif entity.type == "procedure":
            treatment = entity.name
        elif entity.type == "diagnosis":
            diagnosis = entity.name
        elif entity.type == "patient":
            patient = entity.name

    claim_input = ClaimData(
        policy_number=f"POL-{case_id.replace('CASE-', '')[:6]}",
        patient_name=patient,
        hospital_name=hospital,
        diagnosis=diagnosis,
        estimated_cost=case.total_charged if case.total_charged > 0 else 45000.0,
        treatment_plan=treatment,
    )

    pdf_bytes = generate_preauth_pdf(claim_id=f"CLAIM-{case_id.replace('CASE-', '')[:8]}", claim_input=claim_input)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=preauth_{case_id}.pdf"},
    )
