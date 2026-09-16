"""Rule-based Devanagari romanization (#89). Not IndicXlit — see the module docstring."""

import pytest

from kadi.resolution.transliteration import detect_script, romanize_devanagari


@pytest.mark.parametrize(
    "devanagari,expected",
    [
        ("क्रोसिन", "krosin"),                # virama cluster, final schwa deleted
        ("कमला", "kamlaa"),                   # medial schwa deletion
        ("सरकार", "sarkaar"),
        ("हिंदी", "hindii"),                   # anusvara -> n
        ("अंबा", "ambaa"),                     # anusvara before a labial -> m
        ("पॅरासिटामॉल", "peraasitaamol"),      # Marathi ॅ / ॉ vowel signs
        ("सेटीरिज़ीन", "setiiriziin"),          # ज + nukta -> z
        ("मेटफॉर्मिन", "metphormin"),
        ("दुःख", "duhkh"),                     # visarga
    ],
)
def test_romanization_table(devanagari, expected):
    assert romanize_devanagari(devanagari) == expected


def test_precomposed_nukta_letter_matches_decomposed_sequence():
    precomposed = "ज़िंक"      # ज़ as a single code point
    decomposed = "ज़िंक"
    assert romanize_devanagari(precomposed) == romanize_devanagari(decomposed) == "zink"


def test_digits_dandas_mixed_text_and_joiners():
    assert romanize_devanagari("डोलो ६५०") == "dolo 650"
    assert romanize_devanagari("बुखार। खांसी") == "bukhaar khaansii"
    assert romanize_devanagari("Tab क्रोसिन 500 MG") == "tab krosin 500 mg"
    assert romanize_devanagari("क्‍रोसिन") == "krosin"


def test_malformed_input_does_not_raise():
    # A vowel sign with no consonant (OCR noise) and a stray virama.
    assert romanize_devanagari("ि्") == "i"
    assert romanize_devanagari("") == ""


def test_detect_script():
    assert detect_script("Crocin") == "latin"
    assert detect_script("क्रोसिन") == "devanagari"
    assert detect_script("Tab क्रोसिन") == "mixed"
    assert detect_script("650 mg!") == "latin"
    assert detect_script("650") == "none"
    assert detect_script("مرحبا") == "other"
