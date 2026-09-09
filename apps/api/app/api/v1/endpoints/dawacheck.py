"""
DawaCheck API Endpoints.

Handles medicine price benchmarking against NPPA ceiling rates.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

# Import dawacheck packages
from dawacheck.checker import benchmark_medicine, MedicineBenchmark

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine brand '{req.brand_name}' not found in NPPA Schedule-I ceiling price list."
        )
    return benchmark
