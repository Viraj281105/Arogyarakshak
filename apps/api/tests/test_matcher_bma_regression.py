"""Wave 2 / F: the matcher fixes must not turn a correct BMA mapping into a wrong one."""

import json
import pathlib

from app.evaluation.bma import classify
from app.services import billnyay_audit as bn

DATASET = pathlib.Path(__file__).resolve().parents[3] / "data" / "evaluation" / "bma_synthetic.jsonl"

# Rows the OLD substring matcher got right (recorded before the fix; 55 of 78).
CORRECT_BEFORE_FIX = {
    "BMA-%03d" % n for n in range(1, 79)
} - {
    "BMA-025", "BMA-040", "BMA-041", "BMA-042", "BMA-043", "BMA-044", "BMA-045", "BMA-046",
    "BMA-047", "BMA-048", "BMA-049", "BMA-050", "BMA-053", "BMA-054", "BMA-056", "BMA-064",
    "BMA-066", "BMA-069", "BMA-070", "BMA-071", "BMA-073", "BMA-074", "BMA-078",
}


def _rows():
    lines = DATASET.read_text(encoding="utf-8").splitlines()
    return [json.loads(l) for l in lines if l.strip() and "_meta" not in json.loads(l)]


def test_recorded_baseline_has_55_rows():
    assert len(CORRECT_BEFORE_FIX) == 55


def test_every_previously_correct_bma_row_stays_correct():
    regressed = []
    for r in _rows():
        if r["id"] not in CORRECT_BEFORE_FIX:
            continue
        got = bn._match_cghs_key(r["hospital_line"].lower().strip(), bn.CGHS_RATES)
        if classify(r["expected_keys"], got) != "correct":
            regressed.append((r["id"], r["hospital_line"], got))
    assert not regressed, regressed


def test_no_bma_row_is_wrong_key_or_false_match_now():
    bad = []
    for r in _rows():
        got = bn._match_cghs_key(r["hospital_line"].lower().strip(), bn.CGHS_RATES)
        if classify(r["expected_keys"], got) in ("wrong_key", "false_match"):
            bad.append((r["id"], r["hospital_line"], got))
    assert not bad, bad


FORMER_FALSE_MATCHES = ["BMA-064", "BMA-066", "BMA-069", "BMA-070", "BMA-071", "BMA-073", "BMA-074", "BMA-078"]
NEWLY_MAPPED = ["BMA-040", "BMA-041", "BMA-042", "BMA-043", "BMA-044", "BMA-046"]


def _outcome_by_id():
    return {
        r["id"]: classify(r["expected_keys"], bn._match_cghs_key(r["hospital_line"].lower().strip(), bn.CGHS_RATES))
        for r in _rows()
    }


def test_bma_accuracy_does_not_fall_below_the_measured_69_of_78():
    outcomes = _outcome_by_id()
    assert len(outcomes) == 78
    assert sum(1 for o in outcomes.values() if o == "correct") >= 69


def test_former_false_matches_and_newly_mapped_rows_are_correct_by_id():
    outcomes = _outcome_by_id()
    assert {i: outcomes[i] for i in FORMER_FALSE_MATCHES + NEWLY_MAPPED if outcomes[i] != "correct"} == {}


def test_billing_unit_uses_the_same_match_as_the_rate(monkeypatch):
    # Behavioural: 'ppe' inside 'appendectomy' must not supply a per-shift unit either.
    assert bn._billing_unit_of("appendectomy (open)", bn.CGHS_RATES) is None
    assert bn._billing_unit_of("icu day charges", bn.CGHS_RATES) == "per_day"
    # Structural: _billing_unit_of must delegate to _match_cghs_key (a private copy of the
    # matcher would ignore this stub and fall back to its own substring logic).
    monkeypatch.setattr(bn, "_match_cghs_key", lambda name, rates: "dialysis")
    assert bn._billing_unit_of("appendectomy (open)", bn.CGHS_RATES) == "per_session"
