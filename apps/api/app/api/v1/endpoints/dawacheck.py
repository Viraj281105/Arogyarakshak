"""
DawaCheck API Endpoints.

Handles medicine price benchmarking against NPPA ceiling rates.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

# Import dawacheck packages
from dawacheck.checker import REFERENCE_SOURCE, benchmark_medicine, MedicineBenchmark

router = APIRouter()


# --- Pydantic Schemas ---------------------------------------------------------
class BenchRequest(BaseModel):
    brand_name: str = Field(..., description="Brand name of the medicine", json_schema_extra={"example": "Paracetamol 650mg"})
    mrp: float = Field(..., description="Maximum Retail Price (MRP) per tablet/unit", json_schema_extra={"example": 3.5})



# --- Route Implementations ----------------------------------------------------

@router.post("/benchmark", response_model=MedicineBenchmark, status_code=status.HTTP_200_OK)
async def check_medicine_pricing(req: BenchRequest):
    """Checks medicine MRP against NPPA Schedule-I ceiling price list."""
    benchmark = benchmark_medicine(brand_name=req.brand_name, mrp=req.mrp)
    if not benchmark:
        # Do not imply the medicine is uncontrolled — it is simply absent from the curated
        # reference subset this build ships with.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": (
                    f"'{req.brand_name}' is not in ArogyaRakshak's reference price list. "
                    "This does NOT mean the medicine is exempt from price control — the "
                    "reference list is a curated subset of NPPA Schedule-I, not the full "
                    "notified list. Check the NPPA portal before drawing any conclusion."
                ),
                "brand_name": req.brand_name,
                "data_source": REFERENCE_SOURCE,
            },
        )
    return benchmark
