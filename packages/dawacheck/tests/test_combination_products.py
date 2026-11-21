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


# --- combination strengths are never scaled from one component ------------------------
def test_component_strengths_that_sum_to_the_reference_are_not_scaled():
    r = benchmark_medicine("Amoxicillin 500mg + Clavulanate 125mg", 20.0)
    assert r is not None
    assert r.nppa_ceiling_price == 20.10 and r.dosage_normalized is False
    assert r.is_overcharged is False  # 20.00 <= 20.10; scaling by 500/625 used to flag it


@pytest.mark.parametrize("name", [
    "Amoxicillin + Clavulanate 375",          # bare strength that is not the reference combination
    "Amoxicillin 250mg + Clavulanate 125mg",  # components do not add up to 625
    "Augmentin 375mg",
])
def test_other_combination_strengths_are_refused_not_scaled_linearly(name):
    assert benchmark_medicine(name, 10.0) is None


def test_reference_combination_strength_forms_still_map():
    assert benchmark_medicine("Amoxicillin + Clavulanate 625", 20.0).nppa_ceiling_price == 20.10
    assert benchmark_medicine("Augmentin 625 Duo", 20.0).match_method == "exact_or_alias"


def test_amoxicillin_clavulanate_reports_fuzzy_phonetic_as_its_match_method():
    # The combination is resolved through the phonetic path (no new match_method value was added).
    assert benchmark_medicine("Amoxicillin Clavulanate 625", 25.0).match_method == "fuzzy_phonetic"
    assert benchmark_medicine("Amoxicillin and Clavulanate", 25.0).match_method == "fuzzy_phonetic"


# --- combinations written without a marker ---------------------------------------------
@pytest.mark.parametrize("name", [
    "Amoxicillin 500mg Clavulanate", "Paracetamol 650mg Ibuprofen", "Paracetamol 650mg Plus Caffeine",
    "Paracetamol Plus Caffeine",
])
def test_unmarked_or_plus_combinations_are_refused(name):
    assert benchmark_medicine(name, 5.0) is None


# --- pack sizes and codes are not strengths -------------------------------------------
@pytest.mark.parametrize("name", [
    "Dolo 15s", "Dolo 650 x 15", "Dolo strip of 10", "Dolo 650 10's", "Dolo 500 650", "Dolo 5",
    "Paracetmol 10 tablets", "Paracetmol qty 30", "Paracetmol 15 strips", "Paracetmol 10 caps",
    "Paracetmol b12",
])
def test_a_pack_size_or_code_never_rescales_the_ceiling(name):
    r = benchmark_medicine(name, 5.0)
    assert r is not None and r.dosage_normalized is False and r.nppa_ceiling_price == 2.30


def test_a_single_bare_strength_still_scales_and_dolo_1000_scales_up():
    assert benchmark_medicine("Dolo 1000", 5.0).nppa_ceiling_price == 3.54  # 2.30 * 1000/650


# --- false refusals / intended refusals, pinned ----------------------------------------
@pytest.mark.parametrize("name", [
    "Metformin 500mg with meals", "Paracetamol 650mg tablet with food", "Amoxicillin and Clavulanate",
])
def test_dosing_instruction_words_do_not_make_a_single_drug_a_combination(name):
    assert benchmark_medicine(name, 5.0) is not None


@pytest.mark.parametrize("name", [
    # INTENDED refusals: an extra word the entry does not account for (a brand qualifier, an
    # unknown release form, a second pack word) is treated as "a different product" and refused;
    # 'cannot compare' is the safe direction. Documented in docs/evaluation/matcher-fixes.md.
    "Crocin Advance 500mg / 10 tablets",
    "Crocin Advance 500",
    "Metformin Prolonged Release 500mg",
])
def test_intentional_refusals_of_possibly_single_drug_lines(name):
    assert benchmark_medicine(name, 5.0) is None
