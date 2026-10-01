import pytest

from dawacheck.checker import benchmark_medicine


def test_benchmark_medicine_overcharged():
    result = benchmark_medicine("paracetamol 650mg", 3.5)

    assert result is not None
    assert result.active_ingredient == "Paracetamol 650mg"
    assert result.is_overcharged is True
    assert result.deviation_percentage > 0.0


def test_benchmark_medicine_not_overcharged():
    result = benchmark_medicine("amoxicillin 500mg", 5.0)

    assert result is not None
    assert result.is_overcharged is False
    assert result.deviation_percentage == 0.0


def test_benchmark_medicine_not_found():
    result = benchmark_medicine("unknown brand XYZ", 100.0)
    assert result is None


def test_benchmark_medicine_exact_match_reports_match_method():
    result = benchmark_medicine("paracetamol 650mg", 3.5)

    assert result.match_method == "exact_or_alias"
    assert result.dosage_normalized is False
    assert result.reference_dosage_mg == 650.0
    assert result.queried_dosage_mg == 650.0


def test_benchmark_medicine_fuzzy_phonetic_spelling_variant():
    result = benchmark_medicine("Amoxycillin 500mg", 6.0)

    assert result is not None
    assert result.match_method == "fuzzy_phonetic"
    assert result.active_ingredient == "Amoxicillin 500mg"
    assert result.nppa_ceiling_price == 7.49


def test_benchmark_medicine_fuzzy_match_does_not_false_positive():
    result = benchmark_medicine(
        "Completely Unrelated Product",
        100.0,
    )
    assert result is None


def test_benchmark_medicine_official_500mg_paracetamol():
    result = benchmark_medicine("Paracetamol 500mg", 2.0)

    assert result is not None
    assert result.match_method == "exact_or_alias"
    assert result.dosage_normalized is False
    assert result.reference_dosage_mg == 500.0
    assert result.queried_dosage_mg == 500.0
    assert result.nppa_ceiling_price == 0.92
    assert result.is_overcharged is True


def test_benchmark_medicine_dosage_normalization_scales_price_up():
    result = benchmark_medicine("Paracetamol 1000mg", 3.0)

    assert result is not None
    assert result.dosage_normalized is True
    assert result.reference_dosage_mg == 650.0
    assert result.queried_dosage_mg == 1000.0
    assert result.nppa_ceiling_price == 3.14
    assert result.is_overcharged is False


def test_benchmark_medicine_dosage_hint_used_when_brand_name_has_no_strength():
    result = benchmark_medicine(
        "Paracetamol",
        2.0,
        dosage_hint="600mg",
    )

    assert result is not None
    assert result.queried_dosage_mg == 600.0
    assert result.dosage_normalized is True
    assert result.reference_dosage_mg == 650.0
