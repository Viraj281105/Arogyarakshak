"""Whole-word CGHS key matching, modifier refusal and the synonym table (Wave 2 / F)."""

import json
import logging
import os

import pytest

from billnyay import matching
from billnyay.matching import SYNONYM_TABLE_PATH, match_key

RATES_PATH = os.path.join(os.path.dirname(SYNONYM_TABLE_PATH), "cghs_rates.json")
with open(RATES_PATH, encoding="utf-8") as _f:
    RATES = json.load(_f)["rates"]


def m(line):
    return match_key(line.lower().strip(), RATES)


# --- whole-word matching ------------------------------------------------------------
@pytest.mark.parametrize("line", [
    "Appendectomy (Open)", "Lap Appendicectomy", "Endoscopy Upper GI",   # 'ppe' inside a word
    "Particular Care Charges", "Meticulous Dressing Charges",             # 'icu' inside a word
])
def test_key_is_not_matched_inside_a_longer_word(line):
    assert m(line) is None


@pytest.mark.parametrize("line,key", [
    ("ppe kit charges", "ppe kit"),
    ("icu charges - 3 days", "icu"),
    ("mri brain plain", "mri"),
])
def test_whole_word_key_still_matches(line, key):
    assert m(line) == key


def test_exact_key_and_longest_key_preserved():
    assert m("icu day charges") == "icu day charges"
    assert m("semi private ward - 2 days") == "semi private ward"
    assert m("") is None


# --- reverse containment (line is only a fragment of a key) -- decision: refused ---------
@pytest.mark.parametrize("line", ["scan", "ward", "private", "stay", "semi", "knee"])
def test_a_bare_fragment_of_a_key_is_refused(line):
    # Before Wave 2 "scan" -> ct scan and "ward" -> a ward rate by accident of dict order and
    # length; a fragment is ambiguous between several rates, so no rate is applied.
    assert m(line) is None


# --- modifiers that change what is billed ------------------------------------------
@pytest.mark.parametrize("line", [
    "Dialysis Catheter Insertion", "MRI Contrast Agent", "Consultation Report Copy Fee",
    "Cataract Surgery Follow-up Drops", "Cataract Surgery Followup", "Ultrasound Guided Biopsy",
    "Cataract Surgery Follow up",
])
def test_modifier_lines_are_refused_not_mapped_to_the_parent_rate(line):
    assert m(line) is None


@pytest.mark.parametrize("line,key", [
    ("CT Scan Abdomen with contrast", "ct scan"),
    ("CT Scan without contrast", "ct scan"),
])
def test_with_or_without_contrast_describes_the_scan_and_still_maps(line, key):
    assert m(line) == key


# Documented over-refusals: refusing (not benchmarking) is the safe direction, so a line that
# MIGHT be the base procedure but carries a billing-changing word is left un-benchmarked.
@pytest.mark.parametrize("line", [
    "CT Scan Report",                    # a report fee, not a scan
    "Ultrasound Abdomen with report",
    "contrast CT scan",                  # contrast not preceded by with/without
    "CT Scan - contrast",
    "ECG Report Charges",                # (no ECG key either way)
    "Follow up",
])
def test_known_over_refusals_are_intentional(line):
    assert m(line) is None


# --- synonyms: every row of the table is pinned -------------------------------------
@pytest.mark.parametrize("line,key", [
    ("USG Abdomen", "ultrasound"), ("Sonography Pelvis", "ultrasound"),
    ("Ultrasonography Abdomen", "ultrasound"),
    ("X Ray Chest", "x-ray"), ("Xray Knee", "x-ray"), ("X-Ray Chest PA", "x-ray"),
    ("ct-scan chest", "ct scan"),
    ("Angioplasty (PTCA)", "coronary angioplasty"), ("PTCA", "coronary angioplasty"),
    ("PTCA with 1 stent", "coronary angioplasty"),
    ("Haemodialysis Session", "dialysis"), ("Hemodialysis", "dialysis"),
])
def test_small_synonym_table(line, key):
    assert m(line) == key


@pytest.mark.parametrize("line", [
    "Angioplasty", "Peripheral Angioplasty", "Renal Angioplasty", "Carotid Angioplasty", "Cerebral Angioplasty",
    "Femoral Angioplasty", "Pulmonary Angioplasty", "PTA Angioplasty", "Angioplasty with 1 stent",
])
def test_a_bare_or_non_coronary_angioplasty_is_not_assumed_coronary(line):
    # Only an explicit PTCA (or the key wording 'coronary angioplasty') maps; "angioplasty" alone
    # may be peripheral/renal/carotid/... and is refused rather than guessed.
    assert m(line) is None


# --- ambiguity: two unrelated keys with different rates -----------------------------
@pytest.mark.parametrize("line", ["ICU Consultation", "MRI and CT Scan", "Ward Stay and Consultation"])
def test_two_unrelated_keys_with_different_rates_is_refused(line):
    assert m(line) is None


def test_a_refinement_key_is_not_ambiguous():
    assert m("icu day charges x 3") == "icu day charges"      # 'icu' is part of 'icu day charges'
    assert m("syringe infusion pump - 2 days") == "syringe infusion pump"


# --- qualifiers / negation ----------------------------------------------------------
@pytest.mark.parametrize("line", [
    "Non-ICU Ward", "Non ICU Charges", "Step-down ICU", "Stepdown ICU", "Pediatric ICU", "Paediatric ICU",
    "Neonatal ICU Charges", "Ward Stay excluding food", "ICU Charges excluding ventilator",
])
def test_qualified_lines_do_not_map_to_the_plain_rate(line):
    assert m(line) is None


@pytest.mark.parametrize("line", [
    "MRI with Contrast Agent", "CT Scan with Contrast Agent", "MRI contrast media", "CT Scan with contrast injection",
])
def test_contrast_agent_is_refused_even_after_with(line):
    assert m(line) is None


# --- plural folding -----------------------------------------------------------------
@pytest.mark.parametrize("line,key", [
    ("X-Rays", "x-ray"), ("CT Scans", "ct scan"), ("Blood Tests", "blood test"),
    ("Ultrasounds", "ultrasound"), ("Ward Stays", "ward stay"), ("MRIs", "mri"), ("ICUs", "icu"),
    ("Hemodialysis Sessions", "dialysis"), ("USGs", "ultrasound"),
])
def test_plurals_map_like_the_singular(line, key):
    assert m(line) == key


# --- Devanagari ---------------------------------------------------------------------
@pytest.mark.parametrize("line", ["MRI कॉन्ट्रास्ट",
                                  "ECG रिपोर्ट",
                                  "CT Scan रिपोर्ट"])
def test_a_line_with_untranslatable_devanagari_is_refused(line):
    assert m(line) is None


def test_every_synonym_row_maps_to_a_rate_key():
    """Deleting a synonym row is also caught by the parametrized cases above; this guards the
    table itself: each phrase must resolve to a real key in cghs_rates.json."""
    with open(SYNONYM_TABLE_PATH, encoding="utf-8") as f:
        table = json.load(f)
    for row in table["synonyms"]:
        assert m(row["phrase"]) in RATES, f"synonym {row['phrase']!r} maps to no rate key"


# --- the data file must load; a silent empty table would switch refusals off ---------
def test_table_file_exists_loads_and_is_non_empty():
    assert os.path.exists(SYNONYM_TABLE_PATH)
    matching._table.cache_clear()
    table = matching._table()
    assert table["modifiers"] and table["synonyms"] and table["modifier_phrases"]
    assert isinstance(table["clinically_reviewed"], bool)  # review state is recorded, not asserted
    assert table["source_note"]


def test_missing_table_is_logged_as_an_error_not_silent(monkeypatch, caplog):
    monkeypatch.setattr(matching, "SYNONYM_TABLE_PATH", os.path.join(os.path.dirname(SYNONYM_TABLE_PATH), "nope.json"))
    matching._table.cache_clear()
    try:
        with caplog.at_level(logging.ERROR, logger="arogyarakshak.billnyay.matching"):
            matching._table()
        assert any("could not be loaded" in r.getMessage() for r in caplog.records)
    finally:
        monkeypatch.undo()
        matching._table.cache_clear()
