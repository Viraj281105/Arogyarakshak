"""
DawaCheck API Endpoints.

Handles medicine price benchmarking against NPPA ceiling rates.
"""

import logging
import uuid
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.case_auth import require_case_access
from app.clinical.transcription_service import open_tasks_by_entity
from app.consent import require_case_consent
from app.database import get_db
from app.models import DawaCheckGenericMapping, KadiCase, KadiEntity
from kadi.clinical_review.medicine_trust import PendingTask, decide_medicine_trust, trust_summary
# Import dawacheck packages
from dawacheck.checker import (
    REFERENCE_SOURCE,
    benchmark_from_known_generic,
    benchmark_medicine,
    MedicineBenchmark,
)
from dawacheck.prescription_translator import (
    translate_prescription_shorthand,
    PrescriptionTranslation,
)
from dawacheck.prescription_strip_ocr import (
    extract_medicines_from_prescription,
    extract_medicines_from_form,
    PrescriptionStripAnalysis,
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


class CaseMedicineBenchmark(BaseModel):
    entity_id: str = Field(..., description="Kadi entity ID this result was computed for")
    brand_name: str
    benchmark: Optional[MedicineBenchmark] = None
    note: Optional[str] = Field(
        None, description="Set when this medicine could not be benchmarked, and why."
    )
    # ADR-011: where the medicine name used came from. HUMAN_REVIEWED when independent
    # human transcription resolved an uncertain OCR reading; AI_DERIVED otherwise.
    name_provenance: str = "AI_DERIVED"
    transcription_task_id: Optional[str] = None
    transcription_status: Optional[str] = None
    # The trust decision behind this row: state, patient-readable label, whether it was
    # benchmarkable, and (for OCR uncertainty) the reasons it was held back.
    trust: Dict[str, Any] = Field(default_factory=dict)


# --- Route Implementations ----------------------------------------------------

@router.post("/benchmark", response_model=MedicineBenchmark, status_code=status.HTTP_200_OK)
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
    return benchmark


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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported language '{req.language}'. Use en, hi, or mr.",
        )
    return translate_prescription_shorthand(req.instructions, language=req.language)  # type: ignore[arg-type]


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
    # Only a per-unit price is comparable with the per-unit ceiling stored beside it.
    mapping.mrp = benchmark.billed_unit_price


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
    unresolved = await open_tasks_by_entity(db, case_id)

    results: List[CaseMedicineBenchmark] = []
    for entity in medicine_entities:
        meta = entity.meta if isinstance(entity.meta, dict) else {}
        dosage_hint = meta.get("dosage")

        # ADR-011: one trust decision (kadi.clinical_review.medicine_trust) — an OCR
        # reading a human has not settled is never a medication fact, whatever the reason
        # (open or escalated task, unplaced reading, ambiguous/over-cap/ungrounded OCR).
        pending = unresolved.get(entity.id)
        decision = decide_medicine_trust(
            entity.name or "",
            meta,
            PendingTask(
                task_id=pending.id,
                status=pending.status,
                resolved_at=pending.resolved_at.isoformat() if pending.resolved_at else None,
            )
            if pending is not None
            else None,
        )
        trust = trust_summary(decision)
        if not decision.benchmarkable:
            results.append(
                CaseMedicineBenchmark(
                    entity_id=entity.id,
                    brand_name=entity.name,
                    note=decision.note,
                    transcription_task_id=decision.task_id,
                    transcription_status=decision.transcription_status,
                    trust=trust,
                )
            )
            continue

        name_provenance = decision.name_provenance
        brand_name = decision.name

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
                    brand_name=brand_name,
                    note="No cost was recorded for this medicine entity; cannot benchmark.",
                    name_provenance=name_provenance,
                    trust=trust,
                )
            )
            continue

        norm_brand = brand_name.strip().lower()
        # What the document said about quantity/pack (recorded at upload by
        # dawacheck.price_basis.annotate_medicine_price_facts). Entities recorded before
        # that existed fall back to reading their own name. Never the legacy per-unit
        # default: a bill amount of unknown basis is not compared (CANNOT_COMPARE).
        price_facts = meta.get("price_facts") if isinstance(meta.get("price_facts"), dict) else None
        price_kwargs = dict(
            price_facts=price_facts,
            read_name_for_quantity=price_facts is None,
            allow_api_default=False,
        )
        benchmark = benchmark_medicine(brand_name=brand_name, mrp=cost, dosage_hint=dosage_hint, **price_kwargs)

        if benchmark is None:
            # Fall back to a mapping this endpoint learned on an earlier case, before
            # giving up — the reference table's static matcher is not the only memory
            # DawaCheck has of a brand it has already resolved once.
            learned = await _lookup_generic_mapping(db, norm_brand)
            if learned and learned.ceiling_price:
                benchmark = benchmark_from_known_generic(
                    brand_name=brand_name,
                    mrp=cost,
                    active_ingredient=learned.generic_name,
                    ceiling_price=learned.ceiling_price,
                    dosage_hint=dosage_hint,
                    **price_kwargs,
                )

        if benchmark is None:
            results.append(
                CaseMedicineBenchmark(
                    entity_id=entity.id,
                    brand_name=brand_name,
                    note=(
                        f"'{brand_name}' is not in ArogyaRakshak's reference price list. "
                        "This does NOT mean the medicine is exempt from price control."
                    ),
                    name_provenance=name_provenance,
                    trust=trust,
                )
            )
            continue

        await _persist_generic_mapping(db, norm_brand, benchmark)
        results.append(
            CaseMedicineBenchmark(
                entity_id=entity.id, brand_name=brand_name, benchmark=benchmark, name_provenance=name_provenance,
                trust=trust,
            )
        )

    logger.info(
        "[DawaCheck] Benchmarked %d/%d medicine entities for case %s",
        sum(1 for r in results if r.benchmark is not None and r.benchmark.comparison_status.value == "COMPARED"),
        len(medicine_entities),
        case_id,
    )
    return results


class PrescriptionMedicineExtraction(BaseModel):
    """Schema for extracted medicine from prescription/strip photo."""
    name: str = Field(..., description="Medicine name/brand")
    dosage_mg: Optional[float] = Field(None, description="Dosage in milligrams (normalized)")
    quantity: Optional[int] = Field(None, description="Quantity (e.g., 10 for '10 tablets')")
    unit: Optional[str] = Field(None, description="Unit (tablet, capsule, injection, etc.)")
    manufacturer: Optional[str] = Field(None)
    batch_number: Optional[str] = Field(None)
    expiry_date: Optional[str] = Field(None)
    mrp: Optional[float] = Field(None, description="Printed MRP if available")
    confidence: float = Field(1.0, description="Extraction confidence (0.0-1.0)")


class PrescriptionOCRRequest(BaseModel):
    """Request to extract medicines from prescription photo or medicine strip."""
    ocr_text: str = Field(
        ...,
        description="Raw OCR output from Kadi's parse_document, or user-supplied text"
    )
    source: str = Field(
        "kadi_ocr",
        description="Source of the text (kadi_ocr, user_typed, manual_entry, etc.)"
    )


class PrescriptionOCRResponse(BaseModel):
    """Result of prescription photo medicine extraction."""
    medicines: List[PrescriptionMedicineExtraction] = Field(
        default_factory=list,
        description="Extracted medicines from the prescription/strip"
    )
    raw_text: str = Field(default="", description="Raw OCR text (for audit/debugging)")
    parsing_notes: List[str] = Field(
        default_factory=list,
        description="Warnings or notes about parsing (ambiguities, unrecognized formats, etc.)"
    )
    extraction_confidence: float = Field(
        default=1.0,
        description="Overall confidence in the extraction (0.0-1.0)"
    )


@router.post(
    "/ocr/extract-medicines",
    response_model=PrescriptionOCRResponse,
    status_code=status.HTTP_200_OK,
)
async def extract_medicines_from_ocr(
    req: PrescriptionOCRRequest,
):
    """Extracts medicine information from prescription photo or medicine strip OCR text.

    This is a convenience wrapper around the DawaCheck prescription_strip_ocr module,
    for when OCR-extracted text (from Kadi) needs to be parsed into structured
    medicine records before benchmarking against DawaCheck's price reference table.

    Request-body-only: reads no case context, so exempt from consent (like
    /benchmark and /translate-instructions).

    Typical workflow:
      1. Patient uploads a prescription photo or medicine strip photo via Kadi.
      2. Kadi's parse_document performs OCR and returns raw text.
      3. Call this endpoint with the raw text to extract structured medicines.
      4. For each medicine, call /benchmark to check pricing.

    Returns structured medicine data with:
      - name: brand or generic name
      - dosage_mg: normalized dosage
      - quantity & unit: e.g., "10 tablets"
      - manufacturer, batch, expiry: if present on the strip
      - mrp: printed MRP if visible in the photo
      - confidence: how confident the extraction is
    """
    logger.info(
        "[DawaCheck] Extracting medicines from OCR text (source: %s, length: %d)",
        req.source,
        len(req.ocr_text),
    )

    analysis = extract_medicines_from_prescription(
        ocr_text=req.ocr_text,
        source=req.source,
    )

    # Convert to response schema
    medicines_response = [
        PrescriptionMedicineExtraction(
            name=med.name,
            dosage_mg=med.dosage_mg,
            quantity=med.quantity,
            unit=med.unit,
            manufacturer=med.manufacturer,
            batch_number=med.batch_number,
            expiry_date=med.expiry_date,
            mrp=med.mrp,
            confidence=med.confidence,
        )
        for med in analysis.medicines
    ]

    logger.info(
        "[DawaCheck] Extracted %d medicines from OCR text",
        len(medicines_response),
    )

    return PrescriptionOCRResponse(
        medicines=medicines_response,
        raw_text=analysis.raw_text,
        parsing_notes=analysis.parsing_notes,
        extraction_confidence=analysis.extraction_confidence,
    )
