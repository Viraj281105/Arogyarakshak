"""
DawaCheck — Medicine Pricing Intelligence.

Benchmarks MRP against NPPA ceiling prices and suggests generic alternatives.
"""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("DawaCheck.Checker")
logger.setLevel(logging.INFO)


class MedicineBenchmark(BaseModel):
    brand_name: str
    active_ingredient: str
    mrp: float
    nppa_ceiling_price: float
    is_overcharged: bool
    deviation_percentage: float
    generic_substitute_available: bool
    generic_substitute_store_info: str


def benchmark_medicine(brand_name: str, mrp: float) -> Optional[MedicineBenchmark]:
    """Checks medicine MRP against NPPA ceiling prices (mock database check)."""
    logger.info(f"[DawaCheck] Benchmarking medicine: {brand_name} with MRP: {mrp}")
    
    # Mock NPPA Schedule-I database lookup
    # Sourced brand names to active ingredients & ceiling prices
    nppa_database = {
        "paracetamol 650mg": {
            "active_ingredient": "Paracetamol 650mg",
            "ceiling_price": 2.3,  # Price per tablet
        },
        "crocin 650mg": {
            "active_ingredient": "Paracetamol 650mg",
            "ceiling_price": 2.3,
        },
        "amoxicillin 500mg": {
            "active_ingredient": "Amoxicillin 500mg",
            "ceiling_price": 7.5,
        }
    }
    
    key = brand_name.lower().strip()
    if key not in nppa_database:
        logger.warning(f"[DawaCheck] {brand_name} not found in NPPA Schedule-I ceiling list.")
        return None
        
    data = nppa_database[key]
    ceiling = data["ceiling_price"]
    
    # Assuming MRP is per unit/tablet for simplicity
    is_over = mrp > ceiling
    dev_percentage = ((mrp - ceiling) / ceiling) * 100 if is_over else 0.0
    
    benchmark = MedicineBenchmark(
        brand_name=brand_name,
        active_ingredient=data["active_ingredient"],
        mrp=mrp,
        nppa_ceiling_price=ceiling,
        is_overcharged=is_over,
        deviation_percentage=round(dev_percentage, 2),
        generic_substitute_available=True,
        generic_substitute_store_info="A generic equivalent is available at your nearest Jan Aushadhi / PMBJP store.",
    )
    
    logger.info(f"[DawaCheck] Benchmarked {brand_name}: Overcharged={benchmark.is_overcharged}")
    return benchmark
