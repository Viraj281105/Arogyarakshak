"""
DawaCheck — Medicine Pricing Intelligence.

Benchmarks MRP against NPPA ceiling prices and suggests generic alternatives.
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
    mrp: float = Field(
        ...,
        description="The amount as billed/entered, on the basis in `price_basis` (not necessarily "
        "per unit). The per-unit figure compared with the ceiling is `billed_unit_price`.",
    )
    nppa_ceiling_price: float = Field(..., description="Reference ceiling per `unit_label` (one tablet/capsule/vial).")
    # None when the comparison could not be made (`comparison_status` = CANNOT_COMPARE):
    # an unknown answer is never reported as "within ceiling".
    is_overcharged: Optional[bool]
    deviation_percentage: Optional[float]
    generic_substitute_available: bool
    generic_substitute_store_info: str
    data_source: str = Field(
        REFERENCE_SOURCE,
        description="Provenance of the ceiling price. The reference list is a subset, "
        "so absence from it does not mean a medicine is uncontrolled.",
    )
    reference_entry_count: int = Field(
        0, description="Number of formulations in the reference table used for this lookup."
    )
    match_method: str = Field(
        "exact_or_alias",
        description=(
            "How the brand name was resolved to a reference entry: 'exact_or_alias' "
            "(direct name/alias match), 'ingredient_dosage_variant' (same active "
            "ingredient, different strength than the reference entry — price scaled "
            "proportionally), or 'fuzzy_phonetic' (Double Metaphone spelling/OCR-variant "
            "match — lowest confidence, should be shown to the user as a suggestion, "
            "not asserted as certain)."
        ),
    )
    dosage_normalized: bool = Field(
        False,
        description="True when the ceiling price was scaled from a different reference "
        "strength to match the queried dosage, rather than read directly from the table.",
    )
    reference_dosage_mg: Optional[float] = Field(
        None, description="Strength (mg) of the matched reference entry."
    )
    queried_dosage_mg: Optional[float] = Field(
        None, description="Strength (mg) parsed from the query brand name/dosage hint, if any."
    )
    # --- Price basis (see dawacheck.price_basis) ---
    comparison_status: ComparisonStatus = ComparisonStatus.COMPARED
    price_basis: PriceBasis = PriceBasis.PER_UNIT
    price_basis_label: str = "per unit"
    basis_source: str = Field(
        "API_DEFAULT",
        description="Where the basis came from: DECLARED (entered by the person), DOCUMENT_LINE, "
        "DOCUMENT_HEADER (e.g. a 'Rate per tablet' column), API_DEFAULT (legacy manual-API "
        "contract: MRP per unit), NONE.",
    )
    basis_evidence: Optional[str] = Field(None, description="The short text the basis was read from.")
    billed_unit_price: Optional[float] = Field(None, description="Billed price per unit, when it could be worked out.")
    unit_label: str = "unit"
    comparison_reason_code: Optional[str] = None
    comparison_note: Optional[str] = Field(None, description="Why no comparison was made, in plain language.")


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
    """Checks a billed medicine price against NPPA ceiling prices.

    The ceiling is per dosage unit. The billed amount is first resolved to a per-unit
    price (`dawacheck.price_basis`): from the declared basis (`price_basis`,
    `units_per_pack`, `quantity`), from what the document states (`price_facts`) or from
    the name itself ("Dolo 650 (15s)"). When that cannot be done the result carries
    `comparison_status = CANNOT_COMPARE` and no overcharge verdict.
    `allow_api_default` keeps the legacy manual-API contract (an undeclared price whose
    name states no pack is per unit); document-derived callers pass False.

    Resolution order (most to least confident):
      1. Exact reference key, substring, or known alias.
      2. Same active ingredient at a different strength — ceiling price is scaled
         proportionally to the queried dosage (#73).
      3. Double Metaphone phonetic match on the ingredient name, for spelling/OCR
         variants not covered by the alias list (#72).
    Returns None when none of these resolve, rather than guessing.
    """
    logger.info(f"[DawaCheck] Benchmarking medicine: {brand_name} with MRP: {mrp}")

    norm_query = brand_name.lower().strip()
    queried_dosage_mg = extract_dosage_mg(brand_name)
    if queried_dosage_mg is None and dosage_hint:
        queried_dosage_mg = extract_dosage_mg(str(dosage_hint))

    matched_key = None
    matched_data = None
    match_method = "exact_or_alias"

    hit = find_exact_or_alias(norm_query)
    if hit:
        matched_key, matched_data = hit

    if not matched_data:
        bare_query = strip_dosage_token(norm_query)
        if bare_query:
            family = find_ingredient_family(bare_query)
            if family:
                matched_key, matched_data = family[0]
                match_method = "ingredient_dosage_variant"

    if not matched_data:
        phon_hit = find_phonetic_match(norm_query)
        if phon_hit:
            matched_key, matched_data = phon_hit
            match_method = "fuzzy_phonetic"

    if not matched_data:
        # Absent from the curated subset — NOT evidence that the drug is uncontrolled.
        logger.warning(
            "[DawaCheck] '%s' is not in the curated reference list (%d formulations).",
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

    ceiling = matched_data["ceiling_price"]
    reference_dosage_mg = matched_data.get("dosage_mg")
    dosage_normalized = False

    if (
        queried_dosage_mg
        and reference_dosage_mg
        and abs(queried_dosage_mg - reference_dosage_mg) > 0.01
    ):
        ceiling = round(ceiling * (queried_dosage_mg / reference_dosage_mg), 4)
        dosage_normalized = True

    comparison = compare_with_ceiling(billed, ceiling, matched_data.get("unit_form"))

    benchmark = MedicineBenchmark(
        brand_name=brand_name,
        active_ingredient=matched_data["active_ingredient"],
        nppa_ceiling_price=round(ceiling, 2),
        **_price_fields(comparison),
        # Derived, not asserted: only true when the reference entry actually records a
        # generic equivalent for this formulation.
        generic_substitute_available=bool(matched_data.get("generic_info")),
        generic_substitute_store_info=matched_data.get(
            "generic_info",
            "No generic equivalent is recorded for this formulation in the reference list.",
        ),
        data_source=REFERENCE_SOURCE,
        reference_entry_count=len(NPPA_REFERENCE_DATA),
        match_method=match_method,
        dosage_normalized=dosage_normalized,
        reference_dosage_mg=reference_dosage_mg,
        queried_dosage_mg=queried_dosage_mg,
    )

    logger.info(
        "[DawaCheck] Benchmarked %s via %s: %s overcharged=%s",
        brand_name,
        match_method,
        benchmark.comparison_status.value,
        benchmark.is_overcharged,
    )
    return benchmark


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
    """Builds a benchmark from a mapping already resolved elsewhere (e.g. a DawaCheck
    brand->generic mapping learned from an earlier lookup), instead of re-running the
    matcher against the static reference table.

    Used as a fallback when a brand name is not in the curated reference list or its
    aliases/phonetic variants, but a prior lookup already recorded its generic and
    ceiling price (see the DawaCheck-Kadi case integration endpoint, issue #27).
    """
    queried_dosage_mg = extract_dosage_mg(brand_name)
    if queried_dosage_mg is None and dosage_hint:
        queried_dosage_mg = extract_dosage_mg(str(dosage_hint))

    billed = resolve_billed_price(
        mrp,
        name_text=brand_name if read_name_for_quantity else "",
        facts=price_facts,
        allow_api_default=allow_api_default,
    )
    # A learned mapping records no dosage form, so none is checked.
    comparison = compare_with_ceiling(billed, ceiling_price, None)

    return MedicineBenchmark(
        brand_name=brand_name,
        active_ingredient=active_ingredient,
        nppa_ceiling_price=round(ceiling_price, 2),
        **_price_fields(comparison),
        generic_substitute_available=False,
        generic_substitute_store_info=(
            "Resolved from a previously recorded DawaCheck brand mapping; no fresh "
            "generic-availability note is attached to this entry."
        ),
        data_source="DawaCheck learned mapping",
        reference_entry_count=len(NPPA_REFERENCE_DATA),
        match_method="learned_mapping",
        dosage_normalized=False,
        reference_dosage_mg=None,
        queried_dosage_mg=queried_dosage_mg,
    )
