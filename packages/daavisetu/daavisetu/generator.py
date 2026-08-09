"""
DaaviSetu — Claim & Pre-Authorization Form Generator.

Fills common insurance claim forms using parsed Kadi case context.
"""

import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("DaaviSetu.Generator")
logger.setLevel(logging.INFO)


class ClaimData(BaseModel):
    policy_number: str = Field(..., description="Insurance policy ID")
    patient_name: str = Field(..., description="Full name of the patient")
    hospital_name: str = Field(..., description="Name of the hospital")
    diagnosis: str = Field(..., description="ICD-10 clinical diagnosis code or description")
    estimated_cost: float = Field(..., description="Estimated treatment cost")
    treatment_plan: str = Field(..., description="Summary of medical procedure or treatment plan")


class ClaimPackage(BaseModel):
    claim_id: str
    form_data: ClaimData
    form_filled_pdf_path: Optional[str] = None
    status: str = Field("ready_for_review", description='"ready_for_review" | "completed"')


def generate_claim_package(case_id: str, claim_input: ClaimData) -> ClaimPackage:
    """Auto-fills a claim form and returns the structured claim package."""
    logger.info(f"[DaaviSetu] Auto-filling claim form for Case: {case_id}")
    
    # Mocking filling a PDF template path
    mock_pdf_path = f"/data/claims/claim_{case_id}_filled.pdf"
    
    package = ClaimPackage(
        claim_id=f"CLAIM-{case_id[:8]}",
        form_data=claim_input,
        form_filled_pdf_path=mock_pdf_path,
        status="ready_for_review",
    )
    
    logger.info(f"[DaaviSetu] Created claim package {package.claim_id} with status {package.status}")
    return package
