"""verify_citation: a sentence is 'supported' only if every figure it asserts is in the cited span
and every scheme it names is attributed by that span; a sentence that only names a scheme is
'scheme_only'; a figure written as a word or with an unknown unit is 'uncheckable'.

Spans below quote schemesetu.thresholds' own text. Hindi/Marathi sample sentences are
engineer-written test data (NEEDS NATIVE-SPEAKER QA)."""

import time
from types import SimpleNamespace

import pytest

from schemesetu.agent import EligibilityRequest
from schemesetu.citations import CitedSpan, extract_figures, verify_citation
from schemesetu.explain_i18n import build_citation_hits
from schemesetu.reasoning_agent import reason_about_eligibility

MJPJAY_BODY = SimpleNamespace(
    quote=(
        "The GR dated 28 July 2023 implements MJPJAY for all families in the state; the integrated "
        "scheme from 1 July 2024 covers all population of Maharashtra with Rs 5 lakh per family "
        "per year. Rs 1.50 lakh was the 2020-2024 MJPJAY cover."
    )
)
PMJAY_BODY = SimpleNamespace(
    quote=(
        "All senior citizens aged 70 and above are eligible irrespective of income under AB PM-JAY "
        "with a distinct card."
    )
)
# An older-style span whose text BEGINS with the full names of both schemes (a page title).
TITLED_SPAN = SimpleNamespace(
    quote=(
        "Pradhan Mantri Jan Arogya Yojana and Mahatma Jyotirao Phule Jan Arogya Yojana. " + MJPJAY_BODY.quote
    )
)


@pytest.fixture(scope="module")
def hits():
    reasoning = reason_about_eligibility(
        EligibilityRequest(income=1.0, location_state="Maharashtra", medical_need="surgery")
    )
    return build_citation_hits(reasoning)


# ---- wrong-scheme attribution (the HIGH correctness bug) ---------------------
def test_pmjay_sentence_with_the_mjpjay_figure_is_unsupported_against_the_real_span(hits):
    span = hits["MJPJAY:S1"]  # the source page's title names both schemes; its body names MJPJAY only
    v = verify_citation("PMJAY covers Rs 5 lakh per family per year.", span)
    assert v.status == "unsupported" and v.supported is False
    assert v.missing_schemes == ["PMJAY"]


def test_the_right_scheme_with_the_right_figure_is_supported_against_the_real_span(hits):
    v = verify_citation("MJPJAY covers Rs 5 lakh per family per year.", hits["MJPJAY:S1"])
    assert v.status == "supported"


def test_pmjay_sentence_against_a_span_that_starts_with_both_full_names_is_unsupported():
    v = verify_citation("PMJAY covers Rs 5 lakh per family per year.", TITLED_SPAN)
    assert v.status == "unsupported" and v.misattributed_figures == ["500000"]
    assert verify_citation("MJPJAY covers Rs 5 lakh per family per year.", TITLED_SPAN).status == "supported"


def test_mjpjay_sentence_with_the_pmjay_age_is_unsupported_against_the_pmjay_span(hits):
    v = verify_citation("MJPJAY covers every citizen aged 70 and above.", hits["PMJAY:S2"])
    assert v.status == "unsupported" and v.missing_schemes == ["MJPJAY"] and v.missing_figures == []


def test_proximity_window_separates_two_schemes_named_in_one_span():
    body = SimpleNamespace(
        quote="PMJAY covers age 70 and above. " + ("filler words here. " * 30) + "MJPJAY covers Rs 5 lakh."
    )
    assert verify_citation("PMJAY covers age 70.", body).status == "supported"
    assert verify_citation("MJPJAY covers Rs 5 lakh.", body).status == "supported"
    swapped = verify_citation("PMJAY covers Rs 5 lakh.", body)
    assert swapped.status == "unsupported" and swapped.misattributed_figures == ["500000"]


# ---- figure extraction -------------------------------------------------------
def test_extract_figures_normalises_units_digits_and_grouping():
    assert extract_figures("Rs 5 lakh") == {"500000"}
    assert extract_figures("Rs 5-lakh") == {"500000"}
    assert extract_figures("Rs 5,00,000") == {"500000"}
    assert extract_figures("Rs 1.50 lakh") == {"150000"}
    assert extract_figures("₹ 2 crore") == {"20000000"}
    assert extract_figures("५ लाख रुपये") == {"500000"}
    assert extract_figures("५ करोड") == {"50000000"} and extract_figures("५ करोड़") == {"50000000"}
    assert extract_figures("५ कोटी") == {"50000000"}
    assert extract_figures("५० हजार") == {"50000"} and extract_figures("५० हज़ार") == {"50000"}
    assert extract_figures("50 thousand") == {"50000"}
    assert extract_figures("आयु ७०") == {"70"}
    assert extract_figures("2020-2024") == {"2020", "2024"}
    assert extract_figures("[PMJAY:S2] no figures here") == set()  # citation keys are not claims


def test_grouped_numbers_do_not_collapse_when_the_grouping_is_invalid():
    assert extract_figures("60,70") == {"60", "70"}
    assert extract_figures("1,000") == {"1000"} and extract_figures("12,34,567") == {"1234567"}


# ---- supported ---------------------------------------------------------------
def test_supported_when_figures_and_scheme_are_in_the_span():
    v = verify_citation("MJPJAY covers all families with Rs 5 lakh per family per year.", MJPJAY_BODY)
    assert v.status == "supported" and v.supported is True
    assert v.missing_figures == [] and v.missing_schemes == [] and v.unverifiable == []


def test_supported_with_devanagari_digits_script_and_aliases():
    assert verify_citation("PMJAY: ७० वर्ष आयु के सभी नागरिक पात्र हैं।", PMJAY_BODY).supported is True
    assert verify_citation("आयुष्मान भारत में ७० वर्ष की आयु पर कवर है।", PMJAY_BODY).supported is True
    assert verify_citation("महात्मा ज्योतिराव फुले योजना में ५ लाख का कवर है।", MJPJAY_BODY).supported is True
    crore = SimpleNamespace(quote="MJPJAY cover of Rs 5 crore.")
    assert verify_citation("MJPJAY में ५ करोड रुपये का कवर।", crore).supported is True  # NEEDS NATIVE-SPEAKER QA


def test_lakh_and_grouped_rupee_forms_are_equivalent():
    assert verify_citation("MJPJAY cover is Rs 5,00,000 per family.", MJPJAY_BODY).supported is True
    assert verify_citation("MJPJAY cover is Rs 5-lakh per family.", MJPJAY_BODY).supported is True


# ---- unsupported -------------------------------------------------------------
def test_wrong_figure_is_unsupported():
    v = verify_citation("MJPJAY covers Rs 3 lakh per family.", MJPJAY_BODY)
    assert v.status == "unsupported" and v.supported is False and v.missing_figures == ["300000"]


def test_one_wrong_figure_among_correct_ones_fails_the_sentence():
    v = verify_citation("MJPJAY gives Rs 5 lakh from 1 July 2025.", MJPJAY_BODY)
    assert v.supported is False and v.missing_figures == ["2025"]


def test_wrong_age_threshold_is_unsupported():
    v = verify_citation("PMJAY covers every citizen aged 60 and above.", PMJAY_BODY)
    assert v.supported is False and v.missing_figures == ["60"]


def test_scheme_aliases_match_by_compact_name():
    assert verify_citation("AB PM-JAY covers age 70 and above.", PMJAY_BODY).supported is True
    assert verify_citation("Ayushman Bharat PMJAY covers age 70.", PMJAY_BODY).supported is True


def test_empty_inputs_and_objects_without_a_quote_are_unsupported_not_errors():
    assert verify_citation("", MJPJAY_BODY).supported is False
    assert verify_citation("MJPJAY Rs 5 lakh", SimpleNamespace(quote="")).supported is False
    v = verify_citation("MJPJAY Rs 5 lakh", object())
    assert v.status == "unsupported" and v.reasons


# ---- uncheckable / scheme_only -----------------------------------------------
@pytest.mark.parametrize(
    "sentence",
    [
        "MJPJAY covers five lakh rupees.",
        "MJPJAY covers a lakh rupees.",
        "MJPJAY covers Rs 5L per family.",
        "MJPJAY covers Rs 5 L per family.",
        "MJPJAY covers fifty thousand rupees.",
        "MJPJAY में पाँच लाख रुपये का कवर है।",  # NEEDS NATIVE-SPEAKER QA
        "MJPJAY में पन्नास हजार रुपये आहेत.",  # NEEDS NATIVE-SPEAKER QA
        "MJPJAY covers 5 million rupees.",
    ],
)
def test_number_words_and_unknown_units_are_uncheckable_never_supported(sentence):
    v = verify_citation(sentence, MJPJAY_BODY)
    assert v.status == "uncheckable" and v.supported is False and v.unverifiable


def test_a_verified_figure_does_not_rescue_an_unverifiable_one():
    v = verify_citation("MJPJAY covers Rs 5 lakh and five more things.", MJPJAY_BODY)
    assert v.status == "uncheckable"


def test_a_wrong_figure_is_unsupported_even_with_an_unverifiable_word():
    assert verify_citation("MJPJAY covers Rs 3 lakh, five times.", MJPJAY_BODY).status == "unsupported"


def test_scheme_name_only_sentence_gets_a_distinct_status():
    v = verify_citation("MJPJAY applies in Maharashtra.", MJPJAY_BODY)
    assert v.status == "scheme_only" and v.supported is False
    assert verify_citation("PMJAY applies in Maharashtra.", MJPJAY_BODY).status == "unsupported"


def test_sentence_with_no_figure_or_scheme_is_uncheckable_never_supported():
    v = verify_citation("This is a very good scheme.", MJPJAY_BODY)
    assert v.status == "uncheckable" and v.supported is False


def test_unknown_scheme_names_are_not_recognised_so_figures_alone_decide():
    """Only PMJAY and MJPJAY are known. A sentence naming another scheme is checked on its figures
    alone: a documented limitation, pinned here so it cannot change silently."""
    assert verify_citation("XYZ scheme covers Rs 5 lakh.", MJPJAY_BODY).status == "supported"


def test_documented_limit_a_pass_is_not_a_semantic_check():
    """'below 70' vs 'aged 70 and above' passes: only figures and scheme names are compared."""
    assert verify_citation("PMJAY covers citizens below 70.", PMJAY_BODY).status == "supported"


# ---- never raises ------------------------------------------------------------
def test_huge_digit_runs_and_long_decimals_never_raise_and_are_uncheckable():
    start = time.perf_counter()
    for sentence in ("MJPJAY " + "9" * 2_000_000, "MJPJAY 1." + "9" * 40, "MJPJAY " + "9" * 30 + " lakh"):
        v = verify_citation(sentence, MJPJAY_BODY)
        assert v.status == "uncheckable" and v.supported is False
    assert time.perf_counter() - start < 2.0


def test_28_digit_precision_cannot_make_a_wrong_figure_pass():
    span = SimpleNamespace(quote="MJPJAY cover " + "1" * 12 + " lakh")
    assert verify_citation("MJPJAY cover " + "1" * 11 + "2 lakh", span).status != "supported"


def test_cited_span_is_a_plain_value():
    s = CitedSpan(source="u", page=1, quote="q")
    assert s.scheme is None and s.title is None
