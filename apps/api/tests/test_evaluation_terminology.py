"""Hindi/Marathi terminology audit (#37): hand-checked cases for each mechanical check.

The checks surface candidates for a native-speaker review; they never decide a term is wrong."""

import json

from app.evaluation.datasets import DATA_DIR
from app.evaluation.terminology import (
    Entry,
    audit,
    devanagari_words,
    english_words,
    fold,
    glossary_conflicts,
    language_leakage,
    placeholder_mismatch,
    spelling_variants,
    untranslated,
)

GLOSSARY_PATH = DATA_DIR.parent / "terminology" / "glossary.json"


def E(text, lang="hi", source="s", key="k"):
    return Entry(source, key, lang, text)


# ---- folding and tokenising --------------------------------------------------------------------
def test_fold_treats_spelling_variants_as_equal():
    assert fold("जाँच") == fold("जांच")  # chandrabindu vs anusvara
    assert fold("मरीज़") == fold("मरीज")  # nukta
    assert fold("अन्दाज") == fold("अंदाज")  # nasal conjunct vs anusvara
    assert fold("५०० रुपये") == "500 रुपये"
    assert fold("दर") != fold("दरें")  # different words stay different


def test_words_split_on_danda_and_ignore_latin():
    assert devanagari_words("जांच करें। दावा, ok १२") == ["जांच", "करें", "दावा", "१२"]


# ---- spelling variants -------------------------------------------------------------------------
def test_spelling_variants_found_per_language_with_counts():
    entries = [E("जाँच करें"), E("जांच करें"), E("जांच पूरी"), E("जाँच", lang="mr")]
    found = spelling_variants(entries)
    assert len(found) == 1 and found[0]["lang"] == "hi"
    assert found[0]["forms"] == {"जांच": 2, "जाँच": 1}  # marathi has only one form: not a variant


def test_identical_spellings_and_english_are_not_variants():
    assert spelling_variants([E("जांच"), E("जांच"), E("जाँच", lang="en")]) == []


def test_danda_does_not_create_a_variant():
    assert spelling_variants([E("जांच।"), E("जांच")]) == []


# ---- glossary conflicts ------------------------------------------------------------------------
GLOSS = {"concepts": {
    "government": {"en": "government", "hi": ["सरकारी"], "mr": ["सरकारी", "शासकीय"]},
    "price": {"en": "price", "hi": ["दर", "कीमत"], "mr": ["दर"]},
    "insurer": {"en": "insurer", "hi": ["बीमा", "बीमा कंपनी"], "mr": []},
}}


def _by(results, concept, lang):
    return next(r for r in results if r["concept"] == concept and r["lang"] == lang)


def test_two_terms_for_one_concept_in_one_language_is_a_conflict():
    res = glossary_conflicts([E("सरकारी योजना", lang="mr"), E("शासकीय रुग्णालय", lang="mr", key="k2")], GLOSS)
    r = _by(res, "government", "mr")
    assert r["conflict"] and r["distinct_terms"] == ["शासकीय", "सरकारी"]
    assert r["variants_in_use"]["शासकीय"]["examples"] == [("s", "k2")]


def test_a_conflict_needs_both_terms_in_the_same_language():
    res = glossary_conflicts([E("सरकारी योजना", lang="hi"), E("शासकीय योजना", lang="mr")], GLOSS)
    assert not _by(res, "government", "hi")["conflict"] and not _by(res, "government", "mr")["conflict"]


def test_variants_match_whole_words_with_inflection_only():
    inflected = glossary_conflicts([E("नई दरें लागू")], GLOSS)
    assert "दर" in _by(inflected, "price", "hi")["variants_in_use"]
    for not_the_word in ("दर्ज किया", "दरवाजा खुला", "सुंदर घर"):
        assert _by(glossary_conflicts([E(not_the_word)], GLOSS), "price", "hi")["variants_in_use"] == {}, not_the_word


def test_a_variant_that_contains_another_is_one_use_not_two_terms():
    r = _by(glossary_conflicts([E("बीमा कंपनी को सूचित करें")], GLOSS), "insurer", "hi")
    assert set(r["variants_in_use"]) == {"बीमा", "बीमा कंपनी"} and not r["conflict"]


# ---- language leakage --------------------------------------------------------------------------
MARKERS = {"hindi_only": ["नहीं", "है"], "marathi_only": ["नाही", "आहे"]}


def test_hindi_words_in_marathi_and_the_reverse_are_flagged():
    res = language_leakage([E("हे बिल बरोबर नहीं।", lang="mr"), E("यह सही आहे", lang="hi"),
                            E("हे बरोबर नाही", lang="mr"), E("यह सही है", lang="hi")], MARKERS)
    assert [(r["lang"], r["kind"], r["words"]) for r in res] == [
        ("mr", "hindi_in_marathi", ["नहीं"]), ("hi", "marathi_in_hindi", ["आहे"])]


def test_leakage_ignores_placeholders_and_english_entries():
    assert language_leakage([E("{है} नाही", lang="mr"), E("नहीं", lang="en")], MARKERS) == []


# ---- english words, untranslated, placeholders -------------------------------------------------
def test_english_words_respect_allowlist_placeholders_and_case():
    found = english_words([E("IRDAI की {name} policy Policy", source="a"), E("मरीज़ OCR scan", lang="mr", source="b")],
                          allow=["irdai", "OCR"])
    assert set(found) == {"policy", "Policy", "scan"}
    assert found["policy"]["count"] == 1 and found["scan"]["examples"] == [("b", "k", "mr")]
    assert "name" not in found and "IRDAI" not in found and "OCR" not in found


def test_untranslated_finds_identical_text_but_not_bare_placeholders():
    copy = {"src": {"en": {"a": "Check now", "b": "{tier} {status}.", "c": "Done"},
                    "hi": {"a": "Check now", "b": "{tier} {status}.", "c": "पूरा हुआ"},
                    "mr": {"a": "आता तपासा", "b": "{tier} {status}.", "c": "Done"}}}
    assert [(u["lang"], u["key"]) for u in untranslated(copy)] == [("hi", "a"), ("mr", "c")]
    assert untranslated(copy, allow_identical=["Check now", "Done"]) == []


def test_placeholder_mismatch_detects_dropped_added_and_reordered_slots_only_when_set_differs():
    copy = {"src": {"en": {"a": "{n} days left", "b": "{a} and {b}", "c": "Total %s"},
                    "hi": {"a": "दिन बाकी", "b": "{b} और {a}", "c": "कुल %s"},
                    "mr": {"a": "{n} दिवस शिल्लक", "b": "{a}", "c": "एकूण"}}}
    res = placeholder_mismatch(copy)
    assert [(r["lang"], r["key"]) for r in res] == [("hi", "a"), ("mr", "b"), ("mr", "c")]


# ---- end to end and the shipped glossary -------------------------------------------------------
def test_audit_runs_every_check_and_counts_strings():
    copy = {"src": {"en": {"a": "Government scheme"}, "hi": {"a": "सरकारी योजना"}, "mr": {"a": "शासकीय योजना"}}}
    gloss = {**GLOSS, "leakage_markers": MARKERS, "english_allowlist": []}
    letters = [Entry("letters", "x", "mr", "सरकारी रुग्णालय")]
    r = audit(copy, gloss, letters)
    assert r["strings"] == {"en": 1, "hi": 1, "mr": 2}
    assert [c["concept"] for c in r["glossary_conflicts"]] == ["government"]
    assert set(r) >= {"spelling_variants", "language_leakage", "english_words", "untranslated", "placeholder_mismatch"}


def test_the_shipped_glossary_is_well_formed_and_marked_unreviewed():
    g = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
    assert g["_meta"]["status"] == "UNREVIEWED"
    assert len(g["concepts"]) >= 20
    for name, spec in g["concepts"].items():
        assert spec["en"] and spec["hi"] and spec["mr"], name
        assert all(isinstance(v, str) and v for v in spec["hi"] + spec["mr"]), name
    assert set(g["leakage_markers"]) == {"hindi_only", "marathi_only"}
    # a word cannot be both a Hindi-only and a Marathi-only marker
    assert not set(g["leakage_markers"]["hindi_only"]) & set(g["leakage_markers"]["marathi_only"])


# ---- #35 Devanagari OCR ground-truth corpus ------------------------------------------------------
def test_devanagari_ocr_corpus_is_loadable_synthetic_and_scores_through_the_existing_wer_utility():
    from app.evaluation.datasets import load_dataset
    from app.evaluation.ocr_wer import evaluate_ocr

    meta, rows = load_dataset(DATA_DIR / "devanagari_ocr_corpus.jsonl")  # refuses non-synthetic files
    assert meta["synthetic"] is True and meta["reviewed"] is False
    assert len(rows) == 24 and {r["language"] for r in rows} == {"hi", "mr"}
    assert sum(r["language"] == "hi" for r in rows) == sum(r["language"] == "mr" for r in rows) == 12
    assert all(any("\u0900" <= ch <= "\u097f" for ch in r["reference"]) for r in rows)
    perfect = evaluate_ocr(rows, hypotheses={r["id"]: r["reference"] for r in rows})
    assert perfect["rows_scored"] == 24 and perfect["corpus_wer"] == 0 and perfect["corpus_cer"] == 0
    # an English-only engine reading a Devanagari line back as Latin noise scores as total loss
    noisy = evaluate_ocr(rows, hypotheses={r["id"]: "Hl llll lll" for r in rows})
    assert noisy["corpus_cer"] > 0.8
    assert set(noisy["per_error_kind"]) == {"header", "bill_line", "medicine_line", "letter_line", "names",
                                            "digits_dates", "conjunct_heavy", "mixed_script"}
