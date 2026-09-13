import pytest
from dawacheck.checker import benchmark_medicine


def test_benchmark_medicine_overcharged():
    result = benchmark_medicine(brand_name="paracetamol 650mg", mrp=3.5)
    
    assert result is not None
    assert result.active_ingredient == "Paracetamol 650mg"
    assert result.is_overcharged is True
    assert result.deviation_percentage > 0.0
    assert "Jan Aushadhi" in result.generic_substitute_store_info


def test_benchmark_medicine_not_overcharged():
    result = benchmark_medicine(brand_name="amoxicillin 500mg", mrp=5.0)
    
    assert result is not None
    assert result.is_overcharged is False
    assert result.deviation_percentage == 0.0


def test_benchmark_medicine_not_found():
    result = benchmark_medicine(brand_name="unknown brand XYZ", mrp=100.0)
    assert result is None


def test_benchmark_medicine_exact_match_reports_match_method():
    result = benchmark_medicine(brand_name="paracetamol 650mg", mrp=3.5)
    assert result.match_method == "exact_or_alias"
    assert result.dosage_normalized is False
    assert result.reference_dosage_mg == 650.0
    assert result.queried_dosage_mg == 650.0


def test_benchmark_medicine_fuzzy_phonetic_spelling_variant():
    """OCR/spelling variants of a known ingredient (issue #72: Double Metaphone match)."""
    result = benchmark_medicine(brand_name="Amoxycillin 500mg", mrp=6.0)
    assert result is not None
    assert result.match_method == "fuzzy_phonetic"
    assert result.active_ingredient == "Amoxicillin 500mg"
    assert result.nppa_ceiling_price == 7.50


def test_benchmark_medicine_fuzzy_match_does_not_false_positive():
    """A phonetic match must not be fabricated for an unrelated word."""
    result = benchmark_medicine(brand_name="Completely Unrelated Product", mrp=100.0)
    assert result is None


def test_benchmark_medicine_dosage_normalization_scales_price_down():
    """Issue #73: a lower-strength variant of a known ingredient is benchmarked against
    a proportionally scaled ceiling price, not rejected or matched at the wrong strength."""
    result = benchmark_medicine(brand_name="Paracetamol 500mg", mrp=2.0)
    assert result is not None
    assert result.match_method == "ingredient_dosage_variant"
    assert result.dosage_normalized is True
    assert result.reference_dosage_mg == 650.0
    assert result.queried_dosage_mg == 500.0
    # 2.30 * (500/650) = 1.769... -> 1.77
    assert result.nppa_ceiling_price == 1.77
    assert result.is_overcharged is True


def test_benchmark_medicine_dosage_normalization_scales_price_up():
    result = benchmark_medicine(brand_name="Paracetamol 1000mg", mrp=3.0)
    assert result is not None
    assert result.dosage_normalized is True
    # 2.30 * (1000/650) = 3.538... -> 3.54
    assert result.nppa_ceiling_price == 3.54
    assert result.is_overcharged is False


def test_benchmark_medicine_dosage_hint_used_when_brand_name_has_no_strength():
    """Kadi-extracted medicine entities carry dosage separately from the brand name."""
    result = benchmark_medicine(brand_name="Paracetamol", mrp=2.0, dosage_hint="500mg")
    assert result is not None
    assert result.queried_dosage_mg == 500.0
    assert result.dosage_normalized is True
