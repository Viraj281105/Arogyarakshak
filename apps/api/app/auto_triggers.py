"""
Kadi auto-triggering — runs the module checks a case has enough context for (#32, #92).

Technical Documentation §4.4: "Once Kadi has enough context, it can proactively fire other
modules without a re-upload." Readiness rules are declarative and live in
``packages/kadi/kadi/triggers.py``; this module runs the READY, auto-runnable checks and
stores a compact result per check in ``kadi_module_insights``.

Guarantees:

- **Consent-bounded.** The case's stored ``consent_opt_in`` is re-read at run time; without
  it nothing runs and nothing is stored.
- **Same computation as the module routes.** Each check calls the service function its
  own route uses (``build_case_audit``, ``build_case_icd_audit``,
  ``build_case_medicine_benchmarks``, ``build_case_eligibility``), so an insight can never
  disagree with what the module returns when called directly.
- **Read-only analyses only.** DaaviSetu claim generation is never auto-run.
- **Isolated failures.** One failing check is recorded as FAILED with an error id and does
  not stop the others or the upload; the exception text stays in the server log.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.background import get_background_session
from app.models import KadiCase, KadiEntity, KadiModuleInsight, SchemeSetuCaseProfile
from kadi.triggers import (
    ContextSnapshot,
    ModuleReadiness,
    checks_to_run,
    count_entity_types,
    evaluate_readiness,
)

logger = logging.getLogger("arogyarakshak.api.auto_triggers")

# Social category is not collected with the income profile (the engine does not evaluate
# it), so the eligibility request states that plainly instead of assuming "General".
CATEGORY_NOT_PROVIDED = "not provided"


async def context_snapshot(session: AsyncSession, case: KadiCase) -> ContextSnapshot:
    rows = await session.execute(
        select(KadiEntity.type).join(KadiCase.entities).where(KadiCase.id == case.id)
    )
    profile = await session.get(SchemeSetuCaseProfile, case.id)
    return ContextSnapshot(
        consent_opt_in=bool(case.consent_opt_in),
        entity_counts=count_entity_types(t for (t,) in rows.all()),
        has_income_profile=profile is not None,
    )


async def readiness_for_case(session: AsyncSession, case: KadiCase) -> List[ModuleReadiness]:
    return evaluate_readiness(await context_snapshot(session, case))


async def _run_billnyay_audit(session: AsyncSession, case: KadiCase) -> Dict[str, Any]:
    from app.api.v1.endpoints.billnyay import build_case_audit

    audit = await build_case_audit(case.id, session)
    return {
        "total_charged": audit.total_charged,
        "benchmarked_count": audit.benchmarked_count,
        "deviations_count": audit.deviations_count,
        "potential_savings": audit.potential_savings,
        "unmatched_count": audit.unmatched_count,
        "unmatched_amount": audit.unmatched_amount,
    }


async def _run_billnyay_icd_audit(session: AsyncSession, case: KadiCase) -> Dict[str, Any]:
    from app.api.v1.endpoints.billnyay import build_case_icd_audit

    audit = await build_case_icd_audit(case.id, session)
    return {
        "status": audit.status,
        "icd10_code": audit.icd10_code,
        "procedures_billed_count": len(audit.procedures_billed),
        "reference_entry_count": audit.reference_entry_count,
    }


async def _run_dawacheck_benchmark(session: AsyncSession, case: KadiCase) -> Dict[str, Any]:
    from app.api.v1.endpoints.dawacheck import build_case_medicine_benchmarks

    results = await build_case_medicine_benchmarks(case.id, session)
    # A medicine matched to a reference but whose billed amount has no comparable per-unit
    # basis is not "benchmarked": no verdict was reached for it.
    benchmarked = [
        r for r in results if r.benchmark is not None and r.benchmark.comparison_status.value == "COMPARED"
    ]
    return {
        "medicines": len(results),
        "benchmarked": len(benchmarked),
        "overcharged": sum(1 for r in benchmarked if r.benchmark.is_overcharged),
        "price_basis_unclear": sum(
            1 for r in results if r.benchmark is not None and r.benchmark.comparison_status.value != "COMPARED"
        ),
        "not_benchmarked": len(results) - len(benchmarked),
    }


async def _run_schemesetu_eligibility(session: AsyncSession, case: KadiCase) -> Dict[str, Any]:
    from app.api.v1.endpoints.schemesetu import build_case_eligibility

    profile = await session.get(SchemeSetuCaseProfile, case.id)
    results = await build_case_eligibility(
        case.id,
        income=profile.annual_income_inr,
        location_state=profile.state,
        category=CATEGORY_NOT_PROVIDED,
        medical_need=None,
        db=session,
    )
    return {
        "schemes": [
            {
                "scheme_name": r.scheme_name,
                "estimated_eligibility": r.estimated_eligibility,
                "is_provisional": r.is_provisional,
                "criteria_provenance": r.criteria_provenance,
                "criteria_not_evaluated": r.criteria_not_evaluated,
            }
            for r in results
        ],
        "non_determinative_factors": results[0].non_determinative_factors if results else [],
    }


RUNNERS = {
    "billnyay_audit": _run_billnyay_audit,
    "billnyay_icd_audit": _run_billnyay_icd_audit,
    "dawacheck_benchmark": _run_dawacheck_benchmark,
    "schemesetu_eligibility": _run_schemesetu_eligibility,
}


async def upsert_insight(
    session: AsyncSession,
    case_id: str,
    module_check: str,
    *,
    status: str,
    trigger: str,
    summary: Optional[Dict[str, Any]] = None,
    missing_context: Optional[List[str]] = None,
    error_id: Optional[str] = None,
) -> KadiModuleInsight:
    row = (
        await session.execute(
            select(KadiModuleInsight).where(
                KadiModuleInsight.case_id == case_id, KadiModuleInsight.module_check == module_check
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = KadiModuleInsight(id=f"INS-{uuid.uuid4().hex[:10]}", case_id=case_id, module_check=module_check)
        session.add(row)
    row.status = status
    row.trigger = trigger
    row.summary = summary
    row.missing_context = missing_context
    row.error_id = error_id
    row.updated_at = datetime.utcnow()
    return row


async def run_auto_triggers(
    session: AsyncSession, case_id: str, trigger: str, only: Optional[Iterable[str]] = None
) -> List[KadiModuleInsight]:
    """Runs every READY auto-runnable check (optionally restricted to `only`). Checks named
    in `only` that are not ready are recorded as NOT_READY with their missing context.
    The caller commits."""
    case = await session.get(KadiCase, case_id)
    if case is None or not case.consent_opt_in:
        return []

    only_set = set(only) if only is not None else None
    readiness = await readiness_for_case(session, case)
    ran: List[KadiModuleInsight] = []

    for module_check in checks_to_run(readiness, only_set):
        try:
            async with session.begin_nested():
                summary = await RUNNERS[module_check](session, case)
            ran.append(
                await upsert_insight(session, case_id, module_check, status="COMPLETED", trigger=trigger, summary=summary)
            )
        except Exception:
            error_id = uuid.uuid4().hex[:12]
            logger.error("Auto-trigger %s failed [%s] for case=%s", module_check, error_id, case_id, exc_info=True)
            ran.append(
                await upsert_insight(session, case_id, module_check, status="FAILED", trigger=trigger, error_id=error_id)
            )

    if only_set:
        for item in readiness:
            if item.module_check in only_set and item.status == "NOT_READY":
                await upsert_insight(
                    session,
                    case_id,
                    item.module_check,
                    status="NOT_READY",
                    trigger=trigger,
                    missing_context=item.missing_context,
                )

    await session.flush()
    if ran:
        logger.info(
            "Auto-triggered %d module check(s) for case=%s (%s).", len(ran), case_id, trigger
        )
    return ran


async def run_triggers_in_background(case_id: str, trigger: str, only: Optional[List[str]] = None) -> None:
    try:
        async with get_background_session() as session:
            await run_auto_triggers(session, case_id, trigger, only)
            await session.commit()
    except Exception:
        error_id = uuid.uuid4().hex[:12]
        logger.error("Background auto-trigger run failed [%s] for case=%s", error_id, case_id, exc_info=True)
