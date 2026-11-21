"""Whole-word CGHS key matching, modifier refusal and the synonym table (Wave 2 / F)."""

import json
import os

import pytest

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


def test_whole_word_key_still_matches():
    assert m("ppe kit charges") == "ppe kit"
    assert m("icu charges - 3 days") in ("icu", "icu day charges")
    assert m("mri brain plain") == "mri"


def test_exact_key_and_longest_key_preserved():
    assert m("icu day charges") == "icu day charges"
    assert m("semi private ward - 2 days") == "semi private ward"
    assert m("") is None


# --- modifiers that change what is billed ------------------------------------------
@pytest.mark.parametrize("line", [
    "Dialysis Catheter Insertion", "MRI Contrast Agent", "Consultation Report Copy Fee",
    "Cataract Surgery Follow-up Drops", "Cataract Surgery Followup", "Ultrasound Guided Biopsy",
])
def test_modifier_lines_are_refused_not_mapped_to_the_parent_rate(line):
    assert m(line) is None


def test_with_contrast_scan_still_maps():
    assert m("CT Scan Abdomen with contrast") == "ct scan"


# --- synonyms ------------------------------------------------------------------------
@pytest.mark.parametrize("line,key", [
    ("USG Abdomen", "ultrasound"), ("Sonography Pelvis", "ultrasound"),
    ("X Ray Chest", "x-ray"), ("Xray Knee", "x-ray"), ("X-Ray Chest PA", "x-ray"),
    ("ct-scan chest", "ct scan"),
    ("Angioplasty (PTCA)", "coronary angioplasty"), ("PTCA", "coronary angioplasty"),
    ("Haemodialysis Session", "dialysis"), ("Hemodialysis", "dialysis"),
])
def test_small_synonym_table(line, key):
    assert m(line) == key


def test_angioplasty_synonym_refuses_non_coronary_context():
    assert m("Peripheral Angioplasty") is None
    assert m("Renal Angioplasty") is None


def test_synonym_table_is_marked_unreviewed_with_a_source_note():
    with open(SYNONYM_TABLE_PATH, encoding="utf-8") as f:
        table = json.load(f)
    assert table["clinically_reviewed"] is False
    assert table["source_note"]
    assert len(table["synonyms"]) <= 15  # deliberately small
