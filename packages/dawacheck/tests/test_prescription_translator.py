"""Tests for the DawaCheck prescription shorthand translator (#97)."""

import pytest

from dawacheck.prescription_translator import translate_prescription_shorthand, SHORTHAND_REFERENCE


def test_translates_tds_to_three_times_a_day_in_english():
    result = translate_prescription_shorthand("Tab. Dolo 650mg TDS x 5 days", language="en")
    assert result.fully_recognized
    tokens = {i.token.upper(): i.translated for i in result.instructions}
    assert tokens["TDS"] == "three times a day"


def test_translates_bd_to_hindi():
    result = translate_prescription_shorthand("Cap. Amoxicillin 500mg BD after food", language="hi")
    tokens = {i.token.upper(): i.translated for i in result.instructions}
    assert tokens["BD"] == "दिन में दो बार"


def test_translates_qd_to_marathi():
    result = translate_prescription_shorthand("Tab. Metformin 500mg QD", language="mr")
    tokens = {i.token.upper(): i.translated for i in result.instructions}
    assert tokens["QD"] == "दिवसातून एकदा"


def test_recognizes_multiple_distinct_shorthand_tokens_in_one_instruction():
    result = translate_prescription_shorthand("Tab. X 500mg TDS AC, Tab. Y 10mg HS", language="en")
    seen = {i.token.upper() for i in result.instructions}
    assert seen == {"TDS", "AC", "HS"}
    assert result.fully_recognized


def test_hourly_dosing_pattern_is_parsed_parametrically():
    result = translate_prescription_shorthand("Inj. Insulin Q6H", language="en")
    assert result.fully_recognized
    q6h = next(i for i in result.instructions if i.token.upper() == "Q6H")
    assert q6h.meaning_en == "every 6 hours"


def test_hourly_dosing_translates_to_hindi_and_marathi():
    hi = translate_prescription_shorthand("Q4H", language="hi")
    mr = translate_prescription_shorthand("Q4H", language="mr")
    assert hi.instructions[0].translated == "हर 4 घंटे में"
    assert mr.instructions[0].translated == "दर 4 तासांनी"


def test_unrecognized_allcaps_token_is_flagged_not_guessed():
    # ZZZ is not a real medical abbreviation — used deliberately as a probe for an
    # all-caps token this module has never seen. It must never be silently mapped to
    # anything; the anti-fabrication contract is that unknowns are surfaced, not guessed.
    result = translate_prescription_shorthand("Tab. X 5mg ZZZ", language="en")
    assert not result.fully_recognized
    assert "ZZZ" in result.unrecognized_tokens
    zzz = next(i for i in result.instructions if i.token == "ZZZ")
    assert zzz.recognized is False
    assert zzz.meaning_en == ""
    assert zzz.translated == ""


def test_lowercase_shorthand_is_not_matched_by_the_scanning_heuristic():
    # Doctors write shorthand in caps by convention; the scanner deliberately does not
    # treat every lowercase 2-4 letter word as a candidate (it would misfire on
    # ordinary English words like "for", "the", "x5"). This is a documented limitation,
    # not a bug: a caller with pre-tokenized shorthand can call the reference dict
    # directly if they already know the token is shorthand.
    result = translate_prescription_shorthand("tds twice a day", language="en")
    assert result.instructions == []


def test_ordinary_prose_produces_no_false_positive_matches():
    result = translate_prescription_shorthand(
        "Patient advised rest, hydration and follow-up in 3 days.", language="en"
    )
    assert result.instructions == []
    assert result.unrecognized_tokens == []


def test_empty_input_returns_empty_instructions():
    result = translate_prescription_shorthand("", language="en")
    assert result.instructions == []
    assert result.fully_recognized


@pytest.mark.parametrize("token", ["OD", "BD", "TDS", "QDS", "HS", "SOS", "PRN", "AC", "PC", "STAT"])
def test_every_reference_entry_has_all_three_languages(token):
    entry = SHORTHAND_REFERENCE[token]
    for lang in ("en", "hi", "mr"):
        assert entry[lang].strip(), f"{token} missing a {lang} translation"
