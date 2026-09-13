"""
DawaCheck API Endpoints.

Handles medicine price benchmarking against NPPA ceiling rates.
"""

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.consent import require_case_consent
from app.database import get_db
from app.models import DawaCheckGenericMapping, KadiCase, KadiEntity
# Import dawacheck packages
from dawacheck.checker import (
    REFERENCE_SOURCE,
    benchmark_from_known_generic,
    benchmark_medicine,
    MedicineBenchmark,
)

logger = logging.getLogger("arogyarakshak.api.dawacheck")
router = APIRouter()


# --- Pydantic Schemas ---------------------------------------------------------
class BenchRequest(BaseModel):
    brand_name: str = Field(..., description="Brand name of the medicine", json_schema_extra={"example": "Paracetamol 650mg"})
    mrp: float = Field(..., description="Maximum Retail Price (MRP) per tablet/unit", json_schema_extra={"example": 3.5})


class CaseMedicineBenchmark(BaseModel):
    entity_id: str = Field(..., description="Kadi entity ID this result was computed for")
    brand_name: str
    benchmark: Optional[MedicineBenchmark] = None
    note: Optional[str] = Field(
        None, description="Set when this medicine could not be benchmarked, and why."
    )


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


async def _lookup_generic_mapping(
    db: AsyncSession, norm_brand: str
) -> Optional[DawaCheckGenericMapping]:
    result = await db.execute(
        select(DawaCheckGenericMapping).where(DawaCheckGenericMapping.brand_name == norm_brand)
    )
    return result.scalar_one_or_none()


async def _persist_generic_mapping(
    db: AsyncSession, norm_brand: str, benchmark: MedicineBenchmark
) -> None:
    """Upserts the resolved brand->generic mapping.

    `dawacheck_generic_mappings` previously existed with the right shape but was never
    read or written (flagged on issue #27's audit trail). Recording every resolution
    here means a brand matched once via the (slower) fuzzy/dosage path can be recovered
    directly on a later case even if it later falls out of the curated static table.
    """
    mapping = await _lookup_generic_mapping(db, norm_brand)
    if mapping is None:
        mapping = DawaCheckGenericMapping(id=f"MAP-{uuid.uuid4().hex[:10]}", brand_name=norm_brand)
        db.add(mapping)

    mapping.generic_name = benchmark.active_ingredient
    mapping.dosage = (
        f"{benchmark.queried_dosage_mg:g}mg" if benchmark.queried_dosage_mg else None
    )
    mapping.ceiling_price = benchmark.nppa_ceiling_price
    mapping.mrp = benchmark.mrp


@router.get(
    "/cases/{case_id}/benchmark",
    response_model=List[CaseMedicineBenchmark],
    status_code=status.HTTP_200_OK,
)
async def benchmark_case_medicines(case_id: str, db: AsyncSession = Depends(get_db)):
    """Benchmarks every medicine Kadi extracted for this case against NPPA ceiling prices.

    DawaCheck's `/benchmark` route takes all its input from the request body and reads
    no case context, so it is exempt from cross-module consent by design (see
    app.consent). This route is different: it reads entities extracted from the case's
    *uploaded documents* (via Kadi, potentially populated by BillNyay's bill parsing),
    so — like BillNyay and DaaviSetu — it requires the case's consent_opt_in
    (`require_case_consent`) before returning anything.
    """
    await require_case_consent(case_id, db)
    results = await build_case_medicine_benchmarks(case_id, db)
    await db.commit()
    return results


async def build_case_medicine_benchmarks(case_id: str, db: AsyncSession) -> List[CaseMedicineBenchmark]:
    """Benchmarks a case's medicine entities; learned brand mappings are added to the
    session but not committed (the caller commits).

    Shared by the route above and Kadi's auto-triggers (app.auto_triggers, #32) so both
    always compute the same result. Callers must enforce consent first.
    """
    entities_result = await db.execute(
        select(KadiEntity)
        .join(KadiCase.entities)
        .where(KadiCase.id == case_id, KadiEntity.type == "medicine")
    )
    medicine_entities = entities_result.scalars().all()

    results: List[CaseMedicineBenchmark] = []
    for entity in medicine_entities:
        meta = entity.meta if isinstance(entity.meta, dict) else {}
        dosage_hint = meta.get("dosage")

        cost = meta.get("cost")
        if cost is None and entity.value:
            try:
                cost = float(entity.value)
            except (TypeError, ValueError):
                cost = None

        if cost is None:
            results.append(
                CaseMedicineBenchmark(
                    entity_id=entity.id,
                    brand_name=entity.name,
                    note="No cost was recorded for this medicine entity; cannot benchmark.",
                )
            )
            continue

        norm_brand = entity.name.strip().lower()
        benchmark = benchmark_medicine(brand_name=entity.name, mrp=cost, dosage_hint=dosage_hint)

        if benchmark is None:
            # Fall back to a mapping this endpoint learned on an earlier case, before
            # giving up — the reference table's static matcher is not the only memory
            # DawaCheck has of a brand it has already resolved once.
            learned = await _lookup_generic_mapping(db, norm_brand)
            if learned and learned.ceiling_price:
                benchmark = benchmark_from_known_generic(
                    brand_name=entity.name,
                    mrp=cost,
                    active_ingredient=learned.generic_name,
                    ceiling_price=learned.ceiling_price,
                    dosage_hint=dosage_hint,
                )

        if benchmark is None:
            results.append(
                CaseMedicineBenchmark(
                    entity_id=entity.id,
                    brand_name=entity.name,
                    note=(
                        f"'{entity.name}' is not in ArogyaRakshak's reference price list. "
                        "This does NOT mean the medicine is exempt from price control."
                    ),
                )
            )
            continue

        await _persist_generic_mapping(db, norm_brand, benchmark)
        results.append(
            CaseMedicineBenchmark(entity_id=entity.id, brand_name=entity.name, benchmark=benchmark)
        )

    logger.info(
        "[DawaCheck] Benchmarked %d/%d medicine entities for case %s",
        sum(1 for r in results if r.benchmark is not None),
        len(medicine_entities),
        case_id,
    )
    return results
