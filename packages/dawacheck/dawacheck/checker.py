"""
DawaCheck — Medicine Pricing Intelligence.

Benchmarks MRP against NPPA ceiling prices and suggests generic alternatives.
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field

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
    is_overcharged: bool
    deviation_percentage: float
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


def benchmark_medicine(
    brand_name: str, mrp: float, dosage_hint: Optional[str] = None
) -> Optional[MedicineBenchmark]:
    """Checks medicine MRP against NPPA ceiling prices.

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

    is_over = mrp > ceiling
    dev_percentage = ((mrp - ceiling) / ceiling) * 100 if is_over else 0.0

    benchmark = MedicineBenchmark(
        brand_name=brand_name,
        active_ingredient=matched_data["active_ingredient"],
        mrp=mrp,
        nppa_ceiling_price=round(ceiling, 2),
        is_overcharged=is_over,
        deviation_percentage=round(dev_percentage, 2),
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
        "[DawaCheck] Benchmarked %s via %s: Overcharged=%s",
        brand_name,
        match_method,
        benchmark.is_overcharged,
    )
    return benchmark


def benchmark_from_known_generic(
    brand_name: str,
    mrp: float,
    active_ingredient: str,
    ceiling_price: float,
    dosage_hint: Optional[str] = None,
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

    is_over = mrp > ceiling_price
    dev_percentage = ((mrp - ceiling_price) / ceiling_price) * 100 if is_over else 0.0

    return MedicineBenchmark(
        brand_name=brand_name,
        active_ingredient=active_ingredient,
        mrp=mrp,
        nppa_ceiling_price=round(ceiling_price, 2),
        is_overcharged=is_over,
        deviation_percentage=round(dev_percentage, 2),
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
