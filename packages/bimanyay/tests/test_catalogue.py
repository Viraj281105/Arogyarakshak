"""
BimaNyay message catalogue + localised letters (Wave 2, stream D).

The Hindi and Marathi strings in ``bimanyay.catalogue`` are UNREVIEWED engineering-team
text (NEEDS NATIVE-SPEAKER QA). These tests check structure and the absence of English
sentences, never that the wording is correct.
"""

import json
import re
import string
from pathlib import Path

import pytest

from bimanyay import ClaimDenialInput, analyze_insurance_denial, audit_claim_denial, catalogue

HERE = Path(__file__).parent
BASE = dict(policy_number="SYN-0001", insurer_name="Synthetic Insurer Ltd", claimed_amount=100000.0,
            denied_or_deducted_amount=60000.0, diagnosis="Hypertensive crisis",
            denial_reason_raw="Hypertension not disclosed at proposal stage")
CASES = {
    "ped_over_5y": dict(policy_age_years=6.0, denial_category="PED_NON_DISCLOSURE"),
    "ped_under_5y": dict(policy_age_years=2.5, denial_category="PED_NON_DISCLOSURE"),
    "investigation": dict(policy_age_years=3.0, denial_category="INVESTIGATION_ONLY"),
    "room_rent": dict(policy_age_years=2.0, denial_category="ROOM_RENT_CAPPING"),
    "delay": dict(policy_age_years=1.0, denial_category="DELAYED_INTIMATION"),
    "general": dict(policy_age_years=4.0, denial_category="EXCLUSION_CLAUSE"),
    "ped_exactly_5y": dict(policy_age_years=5.0, denial_category="PED_NON_DISCLOSURE"),
    "ped_just_under_5y": dict(policy_age_years=4.99, denial_category="PED_NON_DISCLOSURE"),
    "pre_existing_alias": dict(policy_age_years=6.0, denial_category="PRE_EXISTING"),
    "lowercase_category": dict(policy_age_years=6.0, denial_category="ped_non_disclosure"),
}
# User-supplied fields are Devanagari so that any Latin word left in a hi/mr letter is
# system-generated text (same trick as scripts/terminology_audit.py).
DEVANAGARI_USER = dict(insurer_name="सिंथेटिक बीमा लिमिटेड", diagnosis="उच्च रक्तचाप संकट",
                       denial_reason_raw="प्रस्ताव के समय जानकारी छिपाई गई", policy_number="SYN-0001")

# Latin tokens that may legitimately remain in a Hindi/Marathi letter: acronyms the audit's own
# allow-list carries, the machine marker UNVERIFIED (the evaluation harness counts it), and the
# tokens of a cited circular reference number.
ALLOWED_LATIN = {"irdai", "gro", "crc", "icu", "inr", "unverified", "irda", "hlth", "misc", "cir"}
LATIN = re.compile(r"[A-Za-z][A-Za-z0-9'\-]*")


def latin_words(text: str):
    text = text.replace("SYN-0001", "")  # the user-supplied policy number
    return [w for w in LATIN.findall(text) if w.lower() not in ALLOWED_LATIN and len(w) >= 2]


def _golden():
    return json.loads((HERE / "golden_en_letters.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", sorted(CASES))
def test_english_output_is_byte_identical_to_the_pre_catalogue_output(name):
    golden = _golden()[name]
    result = analyze_insurance_denial(ClaimDenialInput(**golden["input"]))
    assert json.dumps(result.model_dump(), ensure_ascii=False, sort_keys=True) == \
        json.dumps(golden["result"], ensure_ascii=False, sort_keys=True)


@pytest.mark.parametrize("name", sorted(CASES))
def test_unknown_language_falls_back_to_english(name):
    golden = _golden()[name]
    data = ClaimDenialInput(**golden["input"])
    assert analyze_insurance_denial(data, language="fr").model_dump() == analyze_insurance_denial(data).model_dump()


def test_catalogue_covers_every_key_in_every_language():
    for key in catalogue.GROUND_KEYS:
        for lang in catalogue.LANGUAGES:
            assert catalogue.grounds(key, lang, policy_age_years=6.0, diagnosis="X").strip()
    for key in catalogue.VIOLATION_KEYS:
        for lang in catalogue.LANGUAGES:
            v = catalogue.violation(key, lang)
            assert set(v) == {"statute_or_circular", "clause_reference", "violation_summary", "legal_remedy"}
            assert all(s.strip() for s in v.values())


def test_hi_mr_catalogue_entries_are_devanagari_and_not_copies_of_english():
    for key in catalogue.GROUND_KEYS:
        en = catalogue.grounds(key, "en", policy_age_years=6.0, diagnosis="X")
        for lang in ("hi", "mr"):
            text = catalogue.grounds(key, lang, policy_age_years=6.0, diagnosis="X")
            assert text != en and re.search("[ऀ-ॿ]", text)
            assert latin_words(text.replace("X", "")) == [], (key, lang, latin_words(text))
    for key in catalogue.VIOLATION_KEYS:
        for lang in ("hi", "mr"):
            for field, text in catalogue.violation(key, lang).items():
                assert latin_words(text) == [], (key, lang, field, latin_words(text))


def test_placeholders_match_across_languages():
    names = lambda s: sorted(set(re.findall(r"\{(\w+)\}", s)))  # noqa: E731
    for key in catalogue.GROUND_KEYS:
        en = names(catalogue.raw_grounds(key, "en"))
        for lang in ("hi", "mr"):
            assert names(catalogue.raw_grounds(key, lang)) == en, (key, lang)


@pytest.mark.parametrize("lang", ["hi", "mr"])
@pytest.mark.parametrize("name", sorted(CASES))
def test_hi_mr_letters_contain_no_english_sentences(name, lang):
    data = ClaimDenialInput(**BASE, **CASES[name])
    data = data.model_copy(update=DEVANAGARI_USER)
    result = analyze_insurance_denial(data, language=lang)
    for doc in (result.level_1_gro_appeal, result.level_2_bimabharosa_text, result.level_3_ombudsman_grounds):
        assert latin_words(doc) == [], (name, lang, latin_words(doc))


@pytest.mark.parametrize("lang", ["hi", "mr"])
def test_localised_audit_keeps_the_decision_and_prior_unchanged(lang):
    for name, case in CASES.items():
        data = ClaimDenialInput(**BASE, **case)
        en = audit_claim_denial(data)
        loc = audit_claim_denial(data, language=lang)
        assert loc[0] == en[0] and loc[1] == en[1], name
        assert len(loc[3]) == len(en[3]), name


@pytest.mark.parametrize("lang", ["hi", "mr"])
def test_localised_room_rent_citation_keeps_the_unverified_marker(lang):
    data = ClaimDenialInput(**BASE, **CASES["room_rent"])
    violations = audit_claim_denial(data, language=lang)[3]
    assert any(v.clause_reference.startswith("UNVERIFIED") for v in violations)


def test_parameters_are_interpolated():
    data = ClaimDenialInput(**BASE, **CASES["ped_over_5y"])
    for lang in ("hi", "mr"):
        assert "6.0" in audit_claim_denial(data, language=lang)[2]
    inv = ClaimDenialInput(**BASE, **CASES["investigation"])
    for lang in ("hi", "mr"):
        assert "Hypertensive crisis" in audit_claim_denial(inv, language=lang)[2]


def test_no_clinician_opinion_words_in_localised_grounds_or_violation_fields():
    # The grounding harness treats "डॉ..." as a clinician claim that can never be grounded.
    for key in catalogue.GROUND_KEYS:
        for lang in ("hi", "mr"):
            assert "डॉ" not in catalogue.raw_grounds(key, lang)
    for key in catalogue.VIOLATION_KEYS:
        for lang in ("hi", "mr"):
            for field, text in catalogue.violation(key, lang).items():
                assert "डॉ" not in text, (key, lang, field)


def test_hindi_and_marathi_differ_for_every_key_and_field():
    for key in catalogue.GROUND_KEYS:
        assert catalogue.raw_grounds(key, "hi") != catalogue.raw_grounds(key, "mr"), key
    for key in catalogue.VIOLATION_KEYS:
        hi, mr = catalogue.violation(key, "hi"), catalogue.violation(key, "mr")
        for field in hi:
            assert hi[field] != mr[field], (key, field)


def test_key_specific_anchors_are_present_in_every_language():
    for lang in ("hi", "mr"):
        assert "५" in catalogue.raw_grounds("ped_moratorium", lang)
        assert "{policy_age_years}" in catalogue.raw_grounds("ped_moratorium", lang)
        assert "{diagnosis}" in catalogue.raw_grounds("investigation", lang)
        assert "IRDA/HLTH/MISC/CIR/216/09/2011" in catalogue.raw_grounds("delay", lang)
        assert "IRDA/HLTH/MISC/CIR/216/09/2011" in catalogue.violation("delay", lang)["statute_or_circular"]
        assert "ICU" in catalogue.raw_grounds("room_rent", lang)
        assert catalogue.violation("room_rent", lang)["clause_reference"].startswith("UNVERIFIED")
        assert "CRC" in catalogue.violation("crc", lang)["clause_reference"]
        assert "२०२४" in catalogue.violation("moratorium", lang)["statute_or_circular"]


def test_moratorium_clause_number_is_ascii_and_extractable_in_every_language():
    for lang in ("en", "hi", "mr"):
        assert "16" in catalogue.violation("moratorium", lang)["clause_reference"]


def test_violation_placeholders_match_across_languages():
    names = lambda s: sorted(set(re.findall(r"\{(\w+)\}", s)))  # noqa: E731
    for key in catalogue.VIOLATION_KEYS:
        en = catalogue.violation(key, "en")
        for lang in ("hi", "mr"):
            loc = catalogue.violation(key, lang)
            for field in en:
                assert names(loc[field]) == names(en[field]), (key, lang, field)


def test_normalise_language_handles_none_case_and_unknown():
    assert catalogue.normalise_language(None) == "en"
    assert catalogue.normalise_language("") == "en"
    assert catalogue.normalise_language("HI") == "hi"
    assert catalogue.normalise_language("Mr") == "mr"
    assert catalogue.normalise_language("fr") == "en"


def test_five_year_boundary_follows_the_decision_not_the_language():
    five = ClaimDenialInput(**BASE, **CASES["ped_exactly_5y"])
    under = ClaimDenialInput(**BASE, **CASES["ped_just_under_5y"])
    for lang in ("en", "hi", "mr"):
        assert len(audit_claim_denial(five, language=lang)[3]) == 2   # moratorium + CRC
        assert len(audit_claim_denial(under, language=lang)[3]) == 1  # CRC only
