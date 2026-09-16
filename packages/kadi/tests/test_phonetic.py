"""Cross-script Indic phonetic keys (#89)."""

import pytest

from kadi.resolution.phonetic import indic_phonetic_key, phonetic_similarity, soundex


@pytest.mark.parametrize(
    "variants",
    [
        ["Crocin", "Crosin", "क्रोसिन"],
        ["Paracetamol", "पैरासिटामोल", "पॅरासिटामॉल"],
        ["Metformin", "मेटफॉर्मिन"],
        ["Amoxicillin", "Amoxycillin", "अमोक्सिसिलिन"],
        ["Cetirizine", "सेटीरिज़ीन"],
        ["Azithromycin", "एज़िथ्रोमाइसिन"],
        ["Pneumonia", "निमोनिया"],
        ["Angioplasty", "एंजियोप्लास्टी"],
    ],
)
def test_spelling_and_script_variants_share_a_key(variants):
    keys = {indic_phonetic_key(v) for v in variants}
    assert len(keys) == 1, keys


@pytest.mark.parametrize(
    "a,b",
    [("Metformin", "Metoprolol"), ("Amoxicillin", "Ampicillin"), ("मेटफॉर्मिन", "Metoprolol")],
)
def test_different_drugs_do_not_share_a_key(a, b):
    assert indic_phonetic_key(a) != indic_phonetic_key(b)


def test_similarity_ignores_qualifiers_and_word_order():
    result = phonetic_similarity("Tab Paracetamol 650mg", "पॅरासिटामॉल")
    assert result.keys_equal and result.score == 1.0
    assert phonetic_similarity("Type 2 diabetes", "Diabetes type 2").score == 1.0


def test_partial_key_credit_is_halved():
    result = phonetic_similarity("Amoxicillin", "Ampicillin")
    assert not result.keys_equal
    assert 0.0 < result.score <= 0.5


def test_no_identifying_token_is_not_applicable():
    assert phonetic_similarity("650 mg", "Paracetamol").score is None


@pytest.mark.parametrize(
    "word,code",
    [("Robert", "R163"), ("Rupert", "R163"), ("Ashcraft", "A261"), ("Tymczak", "T522"), ("Pfister", "P236")],
)
def test_soundex_baseline_matches_reference_codes(word, code):
    assert soundex(word) == code
