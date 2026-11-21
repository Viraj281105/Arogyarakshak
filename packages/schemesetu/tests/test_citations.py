"""verify_citation: a sentence is supported only if its figures and scheme names are found in
the cited span. Hand-written spans below are quotations of schemesetu.thresholds' own text."""

import pytest
from kadi.retrieval import Hit

from schemesetu.citations import extract_figures, verify_citation

MJPJAY_SPAN = Hit(
    source="https://example.invalid/mjpjay",
    page=1,
    quote=(
        "Pradhan Mantri Jan Arogya Yojana and Mahatma Jyotirao Phule Jan Arogya Yojana. The GR "
        "dated 28 July 2023 implements MJPJAY for all families in the state; the integrated "
        "scheme from 1 July 2024 covers all population of Maharashtra with Rs 5 lakh per family "
        "per year. Rs 1.50 lakh was the 2020-2024 MJPJAY cover."
    ),
    score=0.0,
)
PMJAY_SPAN = Hit(
    source="https://example.invalid/pmjay",
    page=2,
    quote=(
        "Cabinet approves health coverage to all senior citizens of the age 70 years and above "
        "irrespective of income under AB PM-JAY. All senior citizens aged 70 and above are "
        "eligible irrespective of income."
    ),
    score=0.0,
)


# ---- figure extraction -------------------------------------------------------
def test_extract_figures_normalises_units_digits_and_grouping():
    assert extract_figures("Rs 5 lakh") == {"500000"}
    assert extract_figures("Rs 5,00,000") == {"500000"}
    assert extract_figures("Rs 1.50 lakh") == {"150000"}
    assert extract_figures("₹ 2 crore") == {"20000000"}
    assert extract_figures("५ लाख रुपये") == {"500000"}
    assert extract_figures("आयु ७०") == {"70"}
    assert extract_figures("2020-2024") == {"2020", "2024"}
    assert extract_figures("[PMJAY:S2] no figures here") == set()  # citation keys are not claims


# ---- supported ---------------------------------------------------------------
def test_supported_when_figures_and_scheme_are_in_the_span():
    v = verify_citation("MJPJAY covers all families with Rs 5 lakh per family per year.", MJPJAY_SPAN)
    assert v.status == "supported" and v.supported is True
    assert v.missing_figures == [] and v.missing_schemes == []


def test_supported_with_devanagari_digits_and_script():
    v = verify_citation("PMJAY: ७० वर्ष आयु के सभी नागरिक पात्र हैं।", PMJAY_SPAN)
    assert v.supported is True


def test_lakh_and_grouped_rupee_forms_are_equivalent():
    assert verify_citation("MJPJAY cover is Rs 5,00,000 per family.", MJPJAY_SPAN).supported is True


# ---- unsupported -------------------------------------------------------------
def test_wrong_figure_is_unsupported():
    v = verify_citation("MJPJAY covers Rs 3 lakh per family.", MJPJAY_SPAN)
    assert v.status == "unsupported" and v.supported is False
    assert v.missing_figures == ["300000"]


def test_one_wrong_figure_among_correct_ones_fails_the_sentence():
    v = verify_citation("MJPJAY gives Rs 5 lakh from 1 July 2025.", MJPJAY_SPAN)
    assert v.supported is False and v.missing_figures == ["2025"]


def test_wrong_age_threshold_is_unsupported():
    v = verify_citation("PMJAY covers every citizen aged 60 and above.", PMJAY_SPAN)
    assert v.supported is False and v.missing_figures == ["60"]


def test_scheme_name_not_in_the_span_is_unsupported():
    v = verify_citation("MJPJAY covers every citizen aged 70 and above.", PMJAY_SPAN)
    assert v.supported is False and v.missing_schemes == ["MJPJAY"]
    assert v.missing_figures == []


def test_scheme_aliases_match_by_compact_name():
    assert verify_citation("AB PM-JAY covers age 70 and above.", PMJAY_SPAN).supported is True
    assert verify_citation("Ayushman Bharat PMJAY covers age 70.", PMJAY_SPAN).supported is True


# ---- uncheckable -------------------------------------------------------------
def test_sentence_with_no_figure_or_scheme_is_uncheckable_never_supported():
    v = verify_citation("This is a very good scheme.", MJPJAY_SPAN)
    assert v.status == "uncheckable" and v.supported is False


def test_empty_inputs_are_unsupported_not_errors():
    assert verify_citation("", MJPJAY_SPAN).supported is False
    assert verify_citation("MJPJAY Rs 5 lakh", Hit("s", 1, "", 0.0)).supported is False


@pytest.mark.parametrize("sentence", ["Rs 5 lakh", "MJPJAY"])
def test_verdict_reports_what_it_checked(sentence):
    v = verify_citation(sentence, MJPJAY_SPAN)
    assert v.checked_figures or v.checked_schemes
