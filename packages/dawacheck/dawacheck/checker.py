"""
DawaCheck medicine-price benchmarking.

Uses the official NPPA 2025 reference dataset while preserving
legacy DawaCheck aliases and price-basis behavior.
"""

import logging
from typing import Any, Mapping, Optional

from pydantic import BaseModel, Field

from dawacheck.price_basis import (
    ComparisonStatus,
    PriceBasis,
    PriceComparison,
    compare_with_ceiling,
    resolve_billed_price,
)
from dawacheck.reference_data import (
    NPPA_REFERENCE_DATA,
    REFERENCE_SOURCE,
    extract_dosage_mg,
    find_exact_or_alias,
    find_ingredient_family,
    find_phonetic_match,
    strip_dosage_token,
)

logger = logging.getLogger("DawaCheck.Checker")
logger.setLevel(logging.INFO)


class MedicineBenchmark(BaseModel):
    brand_name: str
    active_ingredient: str
    mrp: float
    nppa_ceiling_price: float
    is_overcharged: Optional[bool]
    deviation_percentage: Optional[float]
    generic_substitute_available: bool
    generic_substitute_store_info: str
    data_source: str = Field(default=REFERENCE_SOURCE)
    reference_entry_count: int = 0
    match_method: str = "exact_or_alias"
    dosage_normalized: bool = False
    reference_dosage_mg: Optional[float] = None
    queried_dosage_mg: Optional[float] = None
    comparison_status: ComparisonStatus = ComparisonStatus.COMPARED
    price_basis: PriceBasis = PriceBasis.PER_UNIT
    price_basis_label: str = "per unit"
    basis_source: str = "API_DEFAULT"
    basis_evidence: Optional[str] = None
    billed_unit_price: Optional[float] = None
    unit_label: str = "unit"
    comparison_reason_code: Optional[str] = None
    comparison_note: Optional[str] = None


def _price_fields(comparison: PriceComparison) -> dict:
    return dict(
        mrp=comparison.billed_amount,
        is_overcharged=comparison.is_overcharged,
        deviation_percentage=comparison.deviation_percentage,
        comparison_status=comparison.status,
        price_basis=comparison.price_basis,
        price_basis_label=comparison.price_basis_label,
        basis_source=comparison.basis_source,
        basis_evidence=comparison.basis_evidence,
        billed_unit_price=comparison.billed_unit_price,
        unit_label=comparison.unit_label,
        comparison_reason_code=comparison.reason_code,
        comparison_note=comparison.reason,
    )


def _select_family_reference(
    family: list[tuple[str, dict[str, Any]]],
    queried_dosage_mg: Optional[float],
) -> Optional[tuple[str, dict[str, Any]]]:
    """Select an exact-strength family member, otherwise nearest strength."""

    if not family:
        return None

    if queried_dosage_mg is None:
        # Only safe when one formulation exists.
        return family[0] if len(family) == 1 else None

    exact = [
        item
        for item in family
        if item[1].get("dosage_mg") is not None
        and abs(item[1]["dosage_mg"] - queried_dosage_mg) < 0.01
    ]

    if exact:
        return exact[0]

    with_dosage = [
        item
        for item in family
        if item[1].get("dosage_mg") is not None
    ]

    if not with_dosage:
        return None

    # For a dosage variant, choose the closest recorded strength.
    # This is deterministic and avoids arbitrary family[0] selection.
    return min(
        with_dosage,
        key=lambda item: abs(
            item[1]["dosage_mg"] - queried_dosage_mg
        ),
    )


def benchmark_medicine(
    brand_name: str,
    mrp: float,
    dosage_hint: Optional[str] = None,
    *,
    price_basis: Optional[str] = None,
    units_per_pack: Optional[float] = None,
    quantity: Optional[float] = None,
    price_facts: Optional[Mapping[str, Any]] = None,
    read_name_for_quantity: bool = True,
    allow_api_default: bool = True,
) -> Optional[MedicineBenchmark]:
    logger.info(
        "[DawaCheck] Benchmarking medicine: %s with MRP: %s",
        brand_name,
        mrp,
    )

    queried_dosage_mg = extract_dosage_mg(brand_name)
    if queried_dosage_mg is None and dosage_hint:
        queried_dosage_mg = extract_dosage_mg(str(dosage_hint))

    matched_key = None
    matched_data = None
    match_method = "exact_or_alias"

    # 1. Exact/alias.
    hit = find_exact_or_alias(brand_name)
    if hit:
        matched_key, matched_data = hit

    # 2. Same ingredient, different dosage.
    if matched_data is None:
        bare_query = strip_dosage_token(brand_name)
        if bare_query:
            family = find_ingredient_family(bare_query)
            selected = _select_family_reference(
                family,
                queried_dosage_mg,
            )

            if selected:
                matched_key, matched_data = selected

                reference_dosage = matched_data.get("dosage_mg")
                if (
                    queried_dosage_mg is not None
                    and reference_dosage is not None
                    and abs(
                        queried_dosage_mg - reference_dosage
                    ) > 0.01
                ):
                    match_method = "ingredient_dosage_variant"

    # 3. Conservative spelling/OCR match.
    if matched_data is None:
        phon_hit = find_phonetic_match(brand_name)
        if phon_hit:
            matched_key, matched_data = phon_hit
            match_method = "fuzzy_phonetic"

    if matched_data is None:
        logger.warning(
            "[DawaCheck] '%s' is not in the reference list (%d formulations).",
            brand_name,
            len(NPPA_REFERENCE_DATA),
        )
        return None

    billed = resolve_billed_price(
        mrp,
        declared_basis=price_basis,
        units_per_pack=units_per_pack,
        quantity=quantity,
        name_text=brand_name if read_name_for_quantity else "",
        facts=price_facts,
        allow_api_default=allow_api_default,
    )

    ceiling = float(matched_data["ceiling_price"])
    reference_dosage_mg = matched_data.get("dosage_mg")
    dosage_normalized = False

    if (
        match_method == "ingredient_dosage_variant"
        and queried_dosage_mg is not None
        and reference_dosage_mg is not None
        and abs(
            queried_dosage_mg - reference_dosage_mg
        ) > 0.01
    ):
        ceiling = round(
            ceiling
            * (queried_dosage_mg / reference_dosage_mg),
            4,
        )
        dosage_normalized = True

    comparison = compare_with_ceiling(
        billed,
        ceiling,
        matched_data.get("unit_form"),
    )

    return MedicineBenchmark(
        brand_name=brand_name,
        active_ingredient=matched_data["active_ingredient"],
        nppa_ceiling_price=round(ceiling, 2),
        **_price_fields(comparison),
        generic_substitute_available=bool(
            matched_data.get("generic_info")
        ),
        generic_substitute_store_info=matched_data.get(
            "generic_info",
            "No generic equivalent is recorded for this formulation.",
        ),
        data_source=matched_data.get(
            "reference_source",
            REFERENCE_SOURCE,
        ),
        reference_entry_count=len(NPPA_REFERENCE_DATA),
        match_method=match_method,
        dosage_normalized=dosage_normalized,
        reference_dosage_mg=reference_dosage_mg,
        queried_dosage_mg=queried_dosage_mg,
    )


def benchmark_from_known_generic(
    brand_name: str,
    mrp: float,
    active_ingredient: str,
    ceiling_price: float,
    dosage_hint: Optional[str] = None,
    *,
    price_facts: Optional[Mapping[str, Any]] = None,
    read_name_for_quantity: bool = True,
    allow_api_default: bool = True,
) -> MedicineBenchmark:
    queried_dosage_mg = extract_dosage_mg(brand_name)
    if queried_dosage_mg is None and dosage_hint:
        queried_dosage_mg = extract_dosage_mg(str(dosage_hint))

    billed = resolve_billed_price(
        mrp,
        name_text=brand_name if read_name_for_quantity else "",
        facts=price_facts,
        allow_api_default=allow_api_default,
    )

    comparison = compare_with_ceiling(
        billed,
        ceiling_price,
        None,
    )

    return MedicineBenchmark(
        brand_name=brand_name,
        active_ingredient=active_ingredient,
        nppa_ceiling_price=round(ceiling_price, 2),
        **_price_fields(comparison),
        generic_substitute_available=False,
        generic_substitute_store_info=(
            "Resolved from a previously recorded DawaCheck brand mapping; "
            "no fresh generic-availability note is attached to this entry."
        ),
        data_source="DawaCheck learned mapping",
        reference_entry_count=len(NPPA_REFERENCE_DATA),
        match_method="learned_mapping",
        dosage_normalized=False,
        reference_dosage_mg=None,
        queried_dosage_mg=queried_dosage_mg,
    )
