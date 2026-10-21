"""
BillNyay CGHS audit — application use case.

Moved out of ``app.api.v1.endpoints.billnyay`` (ADR-018) because it is shared by the
audit route, Kadi's auto-triggers, the Claim Pack and the evaluation harness. None of
those callers should import an HTTP endpoint module to reach business logic. The route
module re-exports these names, so existing imports keep working.

Callers must enforce case access and consent before calling the ``build_*`` functions.
"""

import json
import logging
import os
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KadiCase, KadiEntity
from billnyay.agents.icd_audit import ICDProcedureAuditItem, audit_icd_procedure_consistency
from billnyay.explain import explain_audit_line
from billnyay.rate_basis import benchmark_line
from kadi.explanation import Explanation

logger = logging.getLogger("arogyarakshak.api.billnyay")


# --- Load CGHS Rate Schedule Data Source --------------------------------------
# Version label of the loaded rate schedule (None for the hardcoded fallback).
CGHS_VERSION: Optional[str] = None


def _load_cghs_rates() -> Dict[str, Any]:
    candidates: List[str] = []
    # 1. Look up via installed/editable billnyay package
    try:
        import billnyay
        if hasattr(billnyay, "__file__") and billnyay.__file__:
            pkg_dir = os.path.dirname(os.path.abspath(billnyay.__file__))
            candidates.append(os.path.join(pkg_dir, "data", "cghs_rates.json"))
    except Exception as e:
        logger.debug(f"Could not resolve billnyay package directory: {e}")

    # 2. Look up via relative directory paths from this file
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.extend([
        # 4 levels up from apps/api/app/services/billnyay_audit.py -> repo root
        os.path.abspath(os.path.join(current_file_dir, "../../../../packages/billnyay/billnyay/data/cghs_rates.json")),
        os.path.abspath(os.path.join(current_file_dir, "../../../packages/billnyay/billnyay/data/cghs_rates.json")),
        os.path.abspath(os.path.join(os.getcwd(), "packages/billnyay/billnyay/data/cghs_rates.json")),
        os.path.abspath(os.path.join(os.getcwd(), "packages/billnyay/data/cghs_rates.json")),
    ])

    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    rates = data.get("rates", {})
                    if rates:
                        global CGHS_VERSION
                        CGHS_VERSION = data.get("version")
                        logger.info(f"Loaded {len(rates)} CGHS benchmark rates from {path}")
                        return rates
            except Exception as e:
                logger.warning(f"Failed to read CGHS rates from {path}: {e}")

    logger.warning("Using hardcoded CGHS rate fallback; could not locate cghs_rates.json")
    # Fallback dictionary if file not found
    return {
        "consultation": {"benchmark_rate": 350.0, "bundled": False},
        "ward stay": {"benchmark_rate": 1500.0, "bundled": False},
        "x-ray": {"benchmark_rate": 350.0, "bundled": False},
        "blood test": {"benchmark_rate": 250.0, "bundled": False},
        "laparoscopic surgery": {"benchmark_rate": 28000.0, "bundled": False},
    }

CGHS_RATES = _load_cghs_rates()


def _rate_of(entry: Any):
    """Normalises a CGHS rates entry into (benchmark_rate, is_bundled)."""
    if isinstance(entry, dict):
        rate = entry.get("benchmark_rate")
        return (float(rate) if rate is not None else None), bool(entry.get("bundled", False))
    try:
        return float(entry), False
    except (TypeError, ValueError):
        return None, False


def _billing_unit_of(norm_name: str, rates_source: Dict[str, Any]) -> Optional[str]:
    """The matched entry's billing unit (per_day, per_visit, ... per_service), using the
    same longest-substring match as _match_cghs_rate."""
    key = norm_name if norm_name in rates_source else None
    if key is None:
        for k in rates_source:
            if (k in norm_name or norm_name in k) and (key is None or len(k) > len(key)):
                key = k
    entry = rates_source.get(key) if key else None
    return entry.get("billing_unit") if isinstance(entry, dict) else None


def _match_cghs_rate(norm_name: str, rates_source: Dict[str, Any]):
    """Finds the CGHS benchmark for a billed item name.

    Returns (benchmark_rate, is_bundled), or (None, False) when the item has no CGHS
    counterpart. Callers must treat None as "not benchmarked" — never as "fair".

    Among substring candidates the LONGEST key wins, so "icu day charges" is preferred
    over the shorter "icu". The previous implementation returned whichever key dict
    iteration happened to reach first.
    """
    key = _match_cghs_key(norm_name, rates_source)
    if key is None:
        return None, False
    return _rate_of(rates_source[key])


def _match_cghs_key(norm_name: str, rates_source: Dict[str, Any]) -> Optional[str]:
    """The CGHS rate key a billed item name resolves to (exact, else longest substring
    in either direction), or None. Exposed so the evaluation harness (BMA) can score the
    mapping itself rather than only the resulting rate."""
    if not norm_name:
        return None
    if norm_name in rates_source:
        return norm_name

    best_key = None
    for key in rates_source:
        if key in norm_name or norm_name in key:
            if best_key is None or len(key) > len(best_key):
                best_key = key
    return best_key


# --- Result schemas -----------------------------------------------------------
class AuditResultItem(BaseModel):
    item_name: str
    charged: float
    # None when the item has no CGHS counterpart. Previously this defaulted to the
    # charged amount, which made every unrecognised line report a 0% deviation and
    # display as "Fair" — an unchecked charge presented to the patient as verified.
    cghs_benchmark: Optional[float] = None
    deviation_percentage: float
    is_deviation: bool
    benchmarked: bool
    status: Literal["overcharged", "within_benchmark", "bundled", "not_benchmarked"]
    # What the reference covers for this line, e.g. "₹4,500 per day × 3 days"
    # (billnyay.rate_basis). A per-day/visit/bottle rate is never applied to a line that
    # does not say how many days/visits/bottles it covers.
    benchmark_basis: Optional[str] = None
    not_benchmarked_reason: Optional[str] = None
    # "Why am I seeing this?" trail (ADR-017): the evidence, the CGHS row and the
    # reasons anything was not determined. Additive; built from the values above.
    explanation: Optional[Explanation] = None


class AuditResponse(BaseModel):
    case_id: str
    total_charged: float
    # Sums cover benchmarked items only, so potential_savings is never inflated by
    # lines that were never compared against anything.
    total_benchmark: float
    benchmarked_charged: float
    potential_savings: float
    deviations_count: int
    benchmarked_count: int
    unmatched_count: int
    unmatched_amount: float
    audit_items: List[AuditResultItem]


async def build_case_audit(case_id: str, db: AsyncSession) -> AuditResponse:
    """CGHS audit of a case's billing items.

    Shared by the route above and Kadi's auto-triggers (app.auto_triggers, #32) so both
    always compute the same result. Callers must enforce consent first.
    """
    entities_result = await db.execute(
        select(KadiEntity).join(KadiCase.entities)
        .where(KadiCase.id == case_id)
        .where(KadiEntity.type == "billing_item")
    )
    billing_items = entities_result.scalars().all()

    return audit_billing_lines(case_id, billing_items)


def audit_billing_lines(
    case_id: str, billing_items: List[Any], rates_source: Optional[Dict[str, Any]] = None
) -> AuditResponse:
    """Pure CGHS audit of billing lines (objects with ``.name`` and ``.value``).

    Split out of ``build_case_audit`` so the evaluation harness exercises exactly the
    production decision logic without a database.
    """
    audit_items = []
    total_charged = 0.0
    total_benchmark = 0.0
    benchmarked_charged = 0.0
    deviations = 0
    benchmarked_count = 0
    unmatched_count = 0
    unmatched_amount = 0.0

    if rates_source is None:
        rates_source = CGHS_RATES if CGHS_RATES else _load_cghs_rates()

    for item in billing_items:
        norm_name = item.name.lower().strip()
        charged = float(item.value) if item.value else 0.0
        total_charged += charged
        matched_key = _match_cghs_key(norm_name, rates_source)
        exact_match = matched_key is not None and matched_key == norm_name
        item_meta = getattr(item, "meta", None)
        item_meta = item_meta if isinstance(item_meta, dict) else {}

        def _explain(status, benchmark_total, dev, basis, reason, _item=item, _key=matched_key,
                     _exact=exact_match, _meta=item_meta, _charged=charged):
            return explain_audit_line(
                item_name=_item.name, charged=_charged, status=status,
                source_file=_meta.get("source_file"), matched_key=_key,
                matched_entry=rates_source.get(_key) if _key else None, exact_match=_exact,
                rates_version=CGHS_VERSION, benchmark_total=benchmark_total,
                deviation_percentage=dev, benchmark_basis=basis, not_benchmarked_reason=reason,
            )

        matched_rate, is_bundled = _match_cghs_rate(norm_name, rates_source)

        basis_text = None
        if matched_rate is not None and not is_bundled:
            line = benchmark_line(item.name, matched_rate, _billing_unit_of(norm_name, rates_source))
            basis_text = line.basis
            if line.benchmark_total is None:
                unmatched_count += 1
                unmatched_amount += charged
                audit_items.append(
                    AuditResultItem(
                        item_name=item.name,
                        charged=charged,
                        cghs_benchmark=None,
                        deviation_percentage=0.0,
                        is_deviation=False,
                        benchmarked=False,
                        status="not_benchmarked",
                        benchmark_basis=line.basis,
                        not_benchmarked_reason=line.reason,
                        explanation=_explain("not_benchmarked", None, 0.0, line.basis, line.reason),
                    )
                )
                continue
            matched_rate = line.benchmark_total

        if matched_rate is None:
            # No CGHS counterpart. Report this honestly as unverified rather than
            # silently benchmarking the item against its own charge.
            unmatched_count += 1
            unmatched_amount += charged
            audit_items.append(
                AuditResultItem(
                    item_name=item.name,
                    charged=charged,
                    cghs_benchmark=None,
                    deviation_percentage=0.0,
                    is_deviation=False,
                    benchmarked=False,
                    status="not_benchmarked",
                    explanation=_explain("not_benchmarked", None, 0.0, None, None),
                )
            )
            continue

        is_dev = (charged > matched_rate) or is_bundled
        if is_bundled:
            # A bundled item should not be billed separately at all.
            dev_perc = 100.0 if charged > 0 else 0.0
            item_status = "bundled"
        elif is_dev:
            dev_perc = ((charged - matched_rate) / matched_rate) * 100 if matched_rate > 0 else 0.0
            item_status = "overcharged"
        else:
            dev_perc = 0.0
            item_status = "within_benchmark"

        if is_dev:
            deviations += 1

        benchmarked_count += 1
        total_benchmark += matched_rate
        benchmarked_charged += charged
        audit_items.append(
            AuditResultItem(
                item_name=item.name,
                charged=charged,
                cghs_benchmark=matched_rate,
                deviation_percentage=round(dev_perc, 2),
                is_deviation=is_dev,
                benchmarked=True,
                status=item_status,
                benchmark_basis=basis_text,
                explanation=_explain(item_status, matched_rate, round(dev_perc, 2), basis_text, None),
            )
        )

    return AuditResponse(
        case_id=case_id,
        total_charged=round(total_charged, 2),
        total_benchmark=round(total_benchmark, 2),
        benchmarked_charged=round(benchmarked_charged, 2),
        potential_savings=round(max(benchmarked_charged - total_benchmark, 0.0), 2),
        deviations_count=deviations,
        benchmarked_count=benchmarked_count,
        unmatched_count=unmatched_count,
        unmatched_amount=round(unmatched_amount, 2),
        audit_items=audit_items,
    )


async def build_case_icd_audit(case_id: str, db: AsyncSession) -> ICDProcedureAuditItem:
    """Shared by the route above and Kadi's auto-triggers (#32). Callers enforce consent."""
    diagnosis_result = await db.execute(
        select(KadiEntity).join(KadiCase.entities)
        .where(KadiCase.id == case_id, KadiEntity.type == "diagnosis")
    )
    diagnosis_entity = diagnosis_result.scalars().first()
    diagnosis_text = diagnosis_entity.name if diagnosis_entity else ""

    procedure_result = await db.execute(
        select(KadiEntity).join(KadiCase.entities)
        .where(KadiCase.id == case_id, KadiEntity.type == "procedure")
    )
    procedures_billed = [e.name for e in procedure_result.scalars().all() if e.name]

    return audit_icd_procedure_consistency(diagnosis_text, procedures_billed)
