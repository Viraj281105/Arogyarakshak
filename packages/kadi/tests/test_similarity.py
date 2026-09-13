"""String similarity and conflict detection for entity resolution (#28)."""

import pytest

from kadi.resolution.similarity import (
    FACILITY_STOPWORDS,
    GENERIC_STOPWORDS,
    core_tokens,
    dosage_form_conflict,
    extract_quantities,
    jaro_winkler,
    laterality_conflict,
    levenshtein_distance,
    levenshtein_ratio,
    numeric_conflict,
    opposing_prefix_conflict,
    string_similarity,
    tokenize,
    variant_conflict,
)


def test_tokenize_splits_digits_from_letters_and_keeps_devanagari_words_whole():
    assert tokenize("Tab. Dolo 650mg") == ["tab", "dolo", "650", "mg"]
    assert tokenize("Amoxicillin 0.5g") == ["amoxicillin", "0.5", "g"]
    # Vowel signs and the virama are combining marks; they must not split the word.
    assert tokenize("क्रोसिन 500") == ["क्रोसिन", "500"]
    assert tokenize("NaCl 0.9%") == ["nacl", "0.9", "%"]


def test_levenshtein_known_values():
    assert levenshtein_distance("kitten", "sitting") == 3
    assert levenshtein_ratio("kitten", "sitting") == pytest.approx(1 - 3 / 7)
    assert levenshtein_ratio("", "abc") == 0.0
    assert levenshtein_ratio("", "") == 0.0


def test_jaro_winkler_reference_value():
    assert jaro_winkler("martha", "marhta") == pytest.approx(0.9611, abs=1e-4)


def test_quantities_are_normalized_to_milligrams():
    assert extract_quantities(["amoxicillin", "0.5", "g"]) == [500.0]
    assert extract_quantities(["b12", "500", "mcg"]) == [0.5]


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("Dolo 650", "Dolo 500", True),
        ("Room charges day 1", "Room charges day 2", True),
        ("Paracetamol 650mg", "Paracetamol", False),  # missing, not conflicting
        ("Amoxicillin 0.5 g", "Amoxicillin 500 mg", False),  # same strength, other unit
        ("Vitamin D3", "Vitamin D3 60000 IU", False),  # one side only adds a quantity
    ],
)
def test_numeric_conflict(a, b, expected):
    assert numeric_conflict(a, b) is expected


def test_dosage_form_variant_laterality_and_prefix_conflicts():
    assert dosage_form_conflict("Tab Ondansetron 4 mg", "Inj Ondansetron 4 mg")
    assert not dosage_form_conflict("Tab Dolo 650", "Dolo 650 tablet")
    assert not dosage_form_conflict("Dolo 650", "Inj Dolo 650")

    assert variant_conflict("Hepatitis A", "Hepatitis B")
    assert not variant_conflict("Hepatitis A", "Hepatitis")

    assert laterality_conflict("Knee replacement (left)", "Knee replacement Rt")
    assert not laterality_conflict("Knee replacement left", "Knee replacement")

    assert opposing_prefix_conflict("Hyperthyroidism", "Hypothyroidism")
    assert opposing_prefix_conflict("Bradycardia", "Tachycardia")
    assert opposing_prefix_conflict("Pre-operative care", "Post-operative care")
    assert not opposing_prefix_conflict("Hypertension", "Hypertension")
    assert not opposing_prefix_conflict("Metformin", "Metoprolol")


def test_word_order_and_qualifiers_do_not_hide_a_match():
    assert string_similarity("Type 2 diabetes mellitus", "Diabetes mellitus type 2").score == 1.0
    assert string_similarity("Tab Paracetamol 650mg", "Paracetamol").score == 1.0


def test_containment_alone_stays_below_the_merge_band():
    sim = string_similarity("Hypertension", "Pulmonary hypertension")
    assert sim.token_containment == 1.0
    assert sim.score == 0.85


def test_look_alike_drug_names_do_not_count_as_the_same_token():
    sim = string_similarity("Amoxicillin", "Ampicillin")
    assert sim.token_jaccard == 0.0
    assert sim.score == round(1 - 2 / 11, 4)


def test_facility_stopwords_only_apply_when_requested():
    stops = GENERIC_STOPWORDS | FACILITY_STOPWORDS
    assert string_similarity("Sunrise Nursing Home Pvt Ltd", "Sunrise Nursing Home", stops).score == 1.0
    assert string_similarity("Sunrise Nursing Home Pvt Ltd", "Sunrise Nursing Home").score < 1.0


def test_fuzzy_stopwords_are_opt_in_because_they_can_swallow_a_real_name():
    assert core_tokens(["medica", "hospital"], FACILITY_STOPWORDS) == ["medica"]
    assert core_tokens(["medica", "hospital"], FACILITY_STOPWORDS, fuzzy_stopwords=True) == []
