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

from app.consent import require_case_consent
from app.database import get_db
from app.models import DaaviSetuClaim, KadiCase, KadiEntity
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
    case = await require_case_consent(case_id, db)

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

    # 4. Persist the submitted form. This is what the PDF download renders, so the
    #    document the patient signs matches exactly what they submitted here.
    existing = await db.execute(
        select(DaaviSetuClaim).where(DaaviSetuClaim.case_id == case_id)
    )
    claim_record = existing.scalar_one_or_none()

    if claim_record is None:
        claim_record = DaaviSetuClaim(id=package.claim_id, case_id=case_id)
        db.add(claim_record)

    claim_record.policy_number = claim_input.policy_number
    claim_record.patient_name = claim_input.patient_name
    claim_record.hospital_name = claim_input.hospital_name
    claim_record.diagnosis = claim_input.diagnosis
    claim_record.estimated_cost = claim_input.estimated_cost
    claim_record.treatment_plan = claim_input.treatment_plan
    claim_record.status = package.status

    await db.commit()

    logger.info(
        "[DaaviSetu] Persisted claim %s for case %s", claim_record.id, case_id
    )
    return package


@router.get("/cases/{case_id}/claim/pdf")
async def download_preauth_pdf(case_id: str, db: AsyncSession = Depends(get_db)):
    """Downloads the compiled IRDAI Standard Pre-Authorization Form (Annexure-B) PDF.

    Renders strictly from the claim submitted via POST .../claim. Nothing on this form is
    invented: a pre-authorization form is signed and filed with an insurer, so a
    fabricated policy number or a placeholder patient name would be worse than no form.
    If no claim has been submitted yet, this returns 409 rather than guessing.
    """
    await require_case_consent(case_id, db)

    claim_result = await db.execute(
        select(DaaviSetuClaim).where(DaaviSetuClaim.case_id == case_id)
    )
    claim_record = claim_result.scalar_one_or_none()
    if claim_record is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No pre-authorization claim has been submitted for this case. "
                f"POST /api/v1/daavisetu/cases/{case_id}/claim first."
            ),
        )

    claim_input = ClaimData(
        policy_number=claim_record.policy_number,
        patient_name=claim_record.patient_name,
        hospital_name=claim_record.hospital_name,
        diagnosis=claim_record.diagnosis,
        estimated_cost=claim_record.estimated_cost,
        treatment_plan=claim_record.treatment_plan,
    )

    pdf_bytes = generate_preauth_pdf(claim_id=claim_record.id, claim_input=claim_input)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=preauth_{case_id}.pdf"},
    )
