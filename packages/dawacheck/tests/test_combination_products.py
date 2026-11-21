"""Combination products map to a combination entry or are refused; phonetic matches apply the
dosage rule (Wave 2 / F)."""

import pytest

from dawacheck.checker import benchmark_medicine


@pytest.mark.parametrize("name", [
    "Paracetamol + Ibuprofen",
    "Pantoprazole + Domperidone",
    "Paracetamol 650mg + Ibuprofen 400mg",       # contains a listed single-ingredient key verbatim
    "Pantoprazole 40mg & Domperidone 10mg",
    "Metformin 500mg / Glimepiride 1mg",
    "Paracetamol and Ibuprofen",
])
def test_combination_without_a_combination_entry_is_refused(name):
    assert benchmark_medicine(name, 5.0) is None


def test_amoxicillin_clavulanate_maps_to_the_combination_entry_not_plain_amoxicillin():
    r = benchmark_medicine("Amoxicillin Clavulanate 625", 25.0)
    assert r is not None
    assert r.active_ingredient == "Amoxicillin (500mg) + Clavulanic Acid (125mg)"
    assert r.nppa_ceiling_price == 20.10


def test_amoxicillin_plus_clavulanate_maps_to_the_combination_entry():
    r = benchmark_medicine("Amoxicillin + Clavulanate 625", 25.0)
    assert r is not None
    assert r.active_ingredient.startswith("Amoxicillin (500mg) + Clavulanic")


def test_combination_never_maps_to_a_single_ingredient_ceiling():
    for name in ("Amoxicillin + Ibuprofen", "Azithromycin + Cefixime", "Pantoprazole + Domperidone"):
        r = benchmark_medicine(name, 5.0)
        assert r is None, name


def test_extra_unrelated_drug_word_blocks_a_phonetic_match():
    # 'Paracetmol' alone is a spelling variant and still maps; with a second drug it must not.
    assert benchmark_medicine("Paracetmol 650mg", 2.0) is not None
    assert benchmark_medicine("Paracetmol Ibuprofen", 2.0) is None


def test_single_drug_formats_still_map():
    assert benchmark_medicine("Crocin 650mg tablet", 2.0).active_ingredient == "Paracetamol 650mg"
    assert benchmark_medicine("Inj Meropenem 1g", 800.0).active_ingredient.startswith("Meropenem")
    assert benchmark_medicine("Metformin 500mg SR", 2.0) is not None


def test_phonetic_match_applies_the_dosage_rule_to_a_bare_strength():
    r = benchmark_medicine("Dolo 500", 2.0)
    assert r is not None and r.match_method == "fuzzy_phonetic"
    assert r.dosage_normalized is True
    assert r.queried_dosage_mg == 500.0
    assert r.nppa_ceiling_price == 1.77  # 2.30 * 500/650, not the 650 mg ceiling


def test_phonetic_match_with_the_reference_strength_is_not_rescaled():
    r = benchmark_medicine("Dolo650", 2.0)
    assert r is not None and r.dosage_normalized is False
    assert r.nppa_ceiling_price == 2.30
