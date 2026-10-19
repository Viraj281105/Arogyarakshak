"""
DawaCheck case benchmarking — application use case.

Moved out of ``app.api.v1.endpoints.dawacheck`` (ADR-018): shared by the case route,
Kadi's auto-triggers and the Claim Pack. The route module re-exports these names.
Callers must enforce case access and consent first; learned brand mappings are added to
the session but not committed (the caller commits).
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from app.clinical.transcription_service import open_tasks_by_entity
from app.models import DawaCheckGenericMapping, KadiCase, KadiEntity
from dawacheck.checker import (
    MedicineBenchmark,
    benchmark_from_known_generic,
    benchmark_medicine,
)
from dawacheck.explain import explain_medicine
from kadi.clinical_review.medicine_trust import (
    PendingTask,
    decide_medicine_trust,
    name_provenance_class,
    trust_summary,
)
from kadi.explanation import Explanation
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("arogyarakshak.api.dawacheck")


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
    # "Why am I seeing this?" trail (ADR-017). Additive.
    explanation: Optional[Explanation] = None


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
        name_class = name_provenance_class(decision, meta)
        source_file = meta.get("source_file")
        cost = meta.get("cost")
        if cost is None and entity.value:
            try:
                cost = float(entity.value)
            except (TypeError, ValueError):
                cost = None

        def _explain(brand, benchmark=None, note=None, _cls=name_class, _src=source_file, _cost=cost,
                     _trust=trust, _reasons=decision.reasons):
            return explain_medicine(
                brand_name=brand, benchmark=benchmark, name_provenance=_cls,
                trust_code=_trust["state"], trust_label=_trust["label"], trust_detail=None,
                not_compared_note=note, source_file=_src,
                billed_amount=float(_cost) if _cost is not None else None, ocr_reasons=_reasons,
            )

        if not decision.benchmarkable:
            results.append(
                CaseMedicineBenchmark(
                    entity_id=entity.id,
                    brand_name=entity.name,
                    note=decision.note,
                    transcription_task_id=decision.task_id,
                    transcription_status=decision.transcription_status,
                    trust=trust,
                    explanation=_explain(entity.name, note=decision.note),
                )
            )
            continue

        name_provenance = decision.name_provenance
        brand_name = decision.name

        if cost is None:
            results.append(
                CaseMedicineBenchmark(
                    entity_id=entity.id,
                    brand_name=brand_name,
                    note="No cost was recorded for this medicine entity; cannot benchmark.",
                    name_provenance=name_provenance,
                    trust=trust,
                    explanation=_explain(brand_name, note="No cost was recorded for this medicine entity; cannot benchmark."),
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
                    explanation=_explain(
                        brand_name,
                        note="Not found in the curated reference price list; this does NOT mean the medicine is exempt from price control.",
                    ),
                )
            )
            continue

        await _persist_generic_mapping(db, norm_brand, benchmark)
        results.append(
            CaseMedicineBenchmark(
                entity_id=entity.id, brand_name=brand_name, benchmark=benchmark, name_provenance=name_provenance,
                trust=trust, explanation=_explain(brand_name, benchmark=benchmark),
            )
        )

    logger.info(
        "[DawaCheck] Benchmarked %d/%d medicine entities for case %s",
        sum(1 for r in results if r.benchmark is not None and r.benchmark.comparison_status.value == "COMPARED"),
        len(medicine_entities),
        case_id,
    )
    return results
