"""
DawaCheck API Endpoints.

Handles medicine price benchmarking against NPPA ceiling rates.
"""

import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.case_auth import require_case_access
from app.consent import require_case_consent
from app.database import get_db
from app.models import KadiCase
from app.services.dawacheck_benchmarks import (  # noqa: F401 — re-exported for existing importers
    CaseMedicineBenchmark,
    _lookup_generic_mapping,
    _persist_generic_mapping,
    build_case_medicine_benchmarks,
)
from kadi.explanation import Explanation, ProvenanceClass
# Import dawacheck packages
from dawacheck.checker import (
    REFERENCE_SOURCE,
    benchmark_medicine,
    MedicineBenchmark,
)
from dawacheck.explain import explain_medicine
from dawacheck.prescription_translator import (
    translate_prescription_shorthand,
    PrescriptionTranslation,
)

logger = logging.getLogger("arogyarakshak.api.dawacheck")
router = APIRouter()


# --- Pydantic Schemas ---------------------------------------------------------
class BenchRequest(BaseModel):
    brand_name: str = Field(..., description="Brand name of the medicine", json_schema_extra={"example": "Paracetamol 650mg"})
    mrp: float = Field(
        ...,
        description="The price paid, on the basis given in `price_basis`. Without `price_basis` the "
        "legacy contract applies: per tablet/unit, unless the name itself states a pack (e.g. '15s').",
        json_schema_extra={"example": 3.5},
    )
    price_basis: Optional[Literal["PER_UNIT", "PER_STRIP", "PER_PACK", "LINE_TOTAL", "UNKNOWN"]] = Field(
        None, description="What `mrp` buys: one unit, one strip, one pack, or a total for `quantity` units."
    )
    units_per_pack: Optional[float] = Field(None, description="Units in one strip/pack (PER_STRIP / PER_PACK).")
    quantity: Optional[float] = Field(None, description="Units the amount covers (LINE_TOTAL).")


class TranslateInstructionsRequest(BaseModel):
    instructions: str = Field(
        ...,
        description="Free-text doctor instructions containing dosage-frequency shorthand.",
        json_schema_extra={"example": "Tab. Dolo 650mg TDS x 5 days"},
    )
    language: str = Field(
        "en", description="Target language for the translated meaning: en, hi, or mr."
    )


class ExplainedBenchmark(MedicineBenchmark):
    """`MedicineBenchmark` plus its explanation trail (manual check)."""

    explanation: Optional[Explanation] = None


# --- Route Implementations ----------------------------------------------------

@router.post("/benchmark", response_model=ExplainedBenchmark, status_code=status.HTTP_200_OK)
async def check_medicine_pricing(req: BenchRequest):
    """Checks medicine MRP against NPPA Schedule-I ceiling price list."""
    benchmark = benchmark_medicine(
        brand_name=req.brand_name,
        mrp=req.mrp,
        price_basis=req.price_basis,
        units_per_pack=req.units_per_pack,
        quantity=req.quantity,
    )
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
    return ExplainedBenchmark(
        **benchmark.model_dump(),
        explanation=explain_medicine(
            brand_name=req.brand_name,
            benchmark=benchmark,
            name_provenance=ProvenanceClass.USER_ENTERED,
            trust_code="USER_ENTERED",
            trust_label="Entered by you for a manual check",
            trust_detail="Nothing was read from a document; the name and price are exactly what you typed.",
            entered_by_user=True,
        ),
    )


@router.post(
    "/translate-instructions",
    response_model=PrescriptionTranslation,
    status_code=status.HTTP_200_OK,
)
async def translate_instructions(req: TranslateInstructionsRequest):
    """Expands Latin-derived prescription frequency shorthand (TDS, BD, HS, ...) into
    plain language, in the requested language (#97).

    Request-body-only, like `/benchmark` — reads no case context, so it is exempt from
    cross-module consent by design (see app.consent). Only the fixed, standard
    abbreviation set in dawacheck.prescription_translator.SHORTHAND_REFERENCE is
    translated; anything else is returned in `unrecognized_tokens` rather than guessed.
    """
    if req.language not in ("en", "hi", "mr"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unsupported language '{req.language}'. Use en, hi, or mr.",
        )
    return translate_prescription_shorthand(req.instructions, language=req.language)  # type: ignore[arg-type]


@router.get(
    "/cases/{case_id}/benchmark",
    response_model=List[CaseMedicineBenchmark],
    status_code=status.HTTP_200_OK,
)
async def benchmark_case_medicines(
    case_id: str,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Benchmarks every medicine Kadi extracted for this case against NPPA ceiling prices.

    DawaCheck's `/benchmark` route takes all its input from the request body and reads
    no case context, so it is exempt from cross-module consent by design (see
    app.consent). This route is different: it reads entities extracted from the case's
    *uploaded documents* (via Kadi, potentially populated by BillNyay's bill parsing),
    so — like BillNyay and DaaviSetu — it requires the case's consent_opt_in
    (`require_case_consent`) before returning anything.
    """
    require_case_consent(case)
    results = await build_case_medicine_benchmarks(case_id, db)
    await db.commit()
    return results

