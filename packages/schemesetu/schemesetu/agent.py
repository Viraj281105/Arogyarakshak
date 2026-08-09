"""
SchemeSetu — Scheme Eligibility Agent.

Determines estimated eligibility for government healthcare schemes (PMJAY, MJPJAY).
"""

import logging
from typing import Any, Dict, List
from pydantic import BaseModel, Field

logger = logging.getLogger("SchemeSetu.Agent")
logger.setLevel(logging.INFO)


class EligibilityRequest(BaseModel):
    income: float = Field(..., description="Annual family income in INR")
    location_state: str = Field(..., description="State of residence")
    category: str = Field("General", description="Social category (e.g. SC, ST, OBC, General)")
    medical_need: str = Field(..., description="Details of medical procedure or condition")


class SchemeResult(BaseModel):
    scheme_name: str
    estimated_eligibility: str = Field(..., description='"eligible" | "ineligible" | "ambiguous"')
    confidence_score: float
    reason: str
    claim_guide_steps: List[str]


def check_eligibility(request: EligibilityRequest) -> List[SchemeResult]:
    """Check eligibility across PMJAY and MJPJAY based on intake data."""
    logger.info(f"[SchemeSetu] Assessing eligibility for income: {request.income}, state: {request.location_state}")
    
    results = []
    
    # Simple rule-based check for PMJAY (national)
    # PMJAY target is low income / deprived families
    if request.income <= 250000:
        results.append(
            SchemeResult(
                scheme_name="PMJAY (Ayushman Bharat)",
                estimated_eligibility="eligible",
                confidence_score=0.90,
                reason="Annual income is below the ₹2.5L threshold, meeting general economic criteria.",
                claim_guide_steps=[
                    "Verify your name in the SECC-2011 database or via your ration card.",
                    "Visit the nearest empanelled hospital Ayushman Mitra desk.",
                    "Present your Aadhaar card and active Ration Card for verification."
                ]
            )
        )
    else:
        results.append(
            SchemeResult(
                scheme_name="PMJAY (Ayushman Bharat)",
                estimated_eligibility="ineligible",
                confidence_score=0.95,
                reason="Annual income exceeds the ₹2.5L threshold for general PMJAY eligibility.",
                claim_guide_steps=[]
            )
        )

    # Maharashtra MJPJAY check
    if request.location_state.lower() in ["maharashtra", "mh"]:
        if request.income <= 150000:
            results.append(
                SchemeResult(
                    scheme_name="MJPJAY (Mahatma Jyotirao Phule Jan Arogya Yojana)",
                    estimated_eligibility="eligible",
                    confidence_score=0.92,
                    reason="Resident of Maharashtra with annual income under ₹1.5L (Yellow/Orange ration card).",
                    claim_guide_steps=[
                        "Obtain a valid health card or Orange/Yellow ration card.",
                        "Consult an empanelled hospital's Arogyamitra.",
                        "Submit the doctor's diagnosis and treatment plan for pre-authorization."
                    ]
                )
            )
        else:
            results.append(
                SchemeResult(
                    scheme_name="MJPJAY (Mahatma Jyotirao Phule Jan Arogya Yojana)",
                    estimated_eligibility="ineligible",
                    confidence_score=0.85,
                    reason="Annual income is above the ₹1.5L limit for the standard subsidized tier.",
                    claim_guide_steps=[]
                )
            )
            
    return results
