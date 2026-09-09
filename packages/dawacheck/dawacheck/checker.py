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
    
    # Comprehensive NPPA Schedule-I database lookup
    # Sourced brand names to active ingredients, ceiling prices & Jan Aushadhi generic equivalents
    nppa_database = {
        "paracetamol 650mg": {
            "active_ingredient": "Paracetamol 650mg",
            "ceiling_price": 2.30,
            "generic_info": "Generic Paracetamol 650mg available at PMBJP Jan Aushadhi Kendras for ₹0.80/tablet (65% savings).",
            "aliases": ["dolo 650", "dolo 650mg", "crocin 650", "crocin 650mg", "calpol 650", "pacimol 650"],
        },
        "amoxicillin 500mg": {
            "active_ingredient": "Amoxicillin 500mg",
            "ceiling_price": 7.50,
            "generic_info": "Generic Amoxicillin 500mg available at PMBJP Jan Aushadhi for ₹2.40/capsule (68% savings).",
            "aliases": ["mox 500", "novamox 500", "amoxil 500"],
        },
        "augmentin 625": {
            "active_ingredient": "Amoxicillin (500mg) + Clavulanic Acid (125mg)",
            "ceiling_price": 20.10,
            "generic_info": "Generic Amoxyclav 625mg available at PMBJP Kendras for ₹6.50/tablet (68% savings).",
            "aliases": ["augmentin 625 duo", "augmentin 625 duo tablet", "moxikind cv 625", "clavum 625"],
        },
        "metformin 500mg": {
            "active_ingredient": "Metformin Hydrochloride 500mg SR",
            "ceiling_price": 2.15,
            "generic_info": "Generic Metformin 500mg SR available at PMBJP Jan Aushadhi for ₹0.45/tablet (79% savings).",
            "aliases": ["metformin 500mg sr", "glycomet 500", "glyciphage 500", "metformin sr"],
        },
        "meropenem 1g": {
            "active_ingredient": "Meropenem 1000mg Powder for Injection",
            "ceiling_price": 850.00,
            "generic_info": "Generic Meropenem 1g Injection available at Jan Aushadhi stores for ₹245.00/vial (71% savings).",
            "aliases": ["meropenem 1g injection", "meronem 1g", "meromac 1g"],
        },
        "pantoprazole 40mg": {
            "active_ingredient": "Pantoprazole 40mg",
            "ceiling_price": 3.20,
            "generic_info": "Generic Pantoprazole 40mg available at PMBJP Kendras for ₹0.90/tablet (72% savings).",
            "aliases": ["pan 40", "pantocid 40", "pantodac 40"],
        },
        "azithromycin 500mg": {
            "active_ingredient": "Azithromycin 500mg",
            "ceiling_price": 21.50,
            "generic_info": "Generic Azithromycin 500mg available at PMBJP Jan Aushadhi for ₹8.00/tablet (63% savings).",
            "aliases": ["azithral 500", "aziwok 500", "zithrox 500"],
        },
    }

    norm_query = brand_name.lower().strip()
    matched_data = None
    matched_key = None

    # 1. Exact match
    if norm_query in nppa_database:
        matched_data = nppa_database[norm_query]
        matched_key = norm_query

    # 2. Alias / Substring matching
    if not matched_data:
        for primary_key, entry in nppa_database.items():
            if primary_key in norm_query or norm_query in primary_key:
                matched_data = entry
                matched_key = primary_key
                break
            for alias in entry.get("aliases", []):
                if alias in norm_query or norm_query in alias:
                    matched_data = entry
                    matched_key = primary_key
                    break
            if matched_data:
                break

    if not matched_data:
        logger.warning(f"[DawaCheck] '{brand_name}' not found in NPPA Schedule-I ceiling list.")
        return None

    ceiling = matched_data["ceiling_price"]
    is_over = mrp > ceiling
    dev_percentage = ((mrp - ceiling) / ceiling) * 100 if is_over else 0.0

    benchmark = MedicineBenchmark(
        brand_name=brand_name,
        active_ingredient=matched_data["active_ingredient"],
        mrp=mrp,
        nppa_ceiling_price=ceiling,
        is_overcharged=is_over,
        deviation_percentage=round(dev_percentage, 2),
        generic_substitute_available=True,
        generic_substitute_store_info=matched_data.get(
            "generic_info",
            "A generic equivalent is available at your nearest Jan Aushadhi / PMBJP store."
        ),
    )
    
    logger.info(f"[DawaCheck] Benchmarked {brand_name}: Overcharged={benchmark.is_overcharged}")
    return benchmark
