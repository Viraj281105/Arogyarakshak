"""#112: CRR / DPR scorer, with hand-computed expectations."""

import pytest

from app.evaluation.context_reuse import evaluate_context_reuse


def _row(sid, on_req, on_work, off_req, off_work):
    return {"id": sid, "documents": 1,
            "reuse_on": {"requests": on_req, "work": on_work},
            "reuse_off": {"requests": off_req, "work": off_work}}


S1 = _row(
    "S1",
    {"billnyay": {"reused": 3, "fresh": 1}, "dawacheck": {"reused": 2, "fresh": 0}},
    {"ingest": {"ocr": 2, "extraction": 2}},
    {"billnyay": {"fresh": 4}, "dawacheck": {"fresh": 2}},
    {"ingest": {"ocr": 2, "extraction": 2}, "repeat": {"ocr": 6, "extraction": 6}},
)


def test_single_scenario_hand_computed():
    r = evaluate_context_reuse([S1])
    assert (r["n_scenarios"], r["n_requests"], r["reused"]) == (1, 6, 5)
    assert r["crr"] == round(5 / 6, 4)               # 5 of 6 requests reused
    assert (r["current_work"], r["baseline_work"]) == (4, 16)
    assert r["dpr"] == 0.75                           # (16 - 4) / 16
    assert r["per_module_crr"] == {"billnyay": 0.75, "dawacheck": 1.0}


def test_two_scenarios_are_pooled_not_averaged():
    s2 = _row("S2", {"schemesetu": {"reused": 0, "fresh": 2}}, {"ingest": {"ocr": 1, "extraction": 1}},
              {"schemesetu": {"fresh": 2}}, {"ingest": {"ocr": 1, "extraction": 1}, "repeat": {"ocr": 2, "extraction": 2}})
    r = evaluate_context_reuse([S1, s2])
    assert (r["n_requests"], r["reused"]) == (8, 5)
    assert r["crr"] == round(5 / 8, 4)               # pooled; the mean of 0.8333 and 0 would be 0.4167
    assert (r["current_work"], r["baseline_work"]) == (6, 22)
    assert r["dpr"] == round(16 / 22, 4)
    assert [s["crr"] for s in r["per_scenario"]] == [round(5 / 6, 4), 0.0]
    assert r["per_scenario"][1]["dpr"] == round(4 / 6, 4)  # (6 - 2) / 6


def test_no_reuse_and_no_savings_edge_cases():
    none = _row("N", {"billnyay": {"fresh": 2}}, {"ingest": {"ocr": 1}},
                {"billnyay": {"fresh": 2}}, {"ingest": {"ocr": 1}})
    r = evaluate_context_reuse([none])
    assert r["crr"] == 0.0 and r["dpr"] == 0.0
    empty = evaluate_context_reuse([_row("E", {}, {}, {}, {})])
    assert empty["crr"] is None and empty["dpr"] is None  # undefined, never reported as 0 or 1
    assert evaluate_context_reuse([])["crr"] is None


@pytest.mark.parametrize("bad", [-1, 1.5, True, "3"])
def test_rejects_invalid_counts(bad):
    row = _row("X", {"billnyay": {"reused": bad}}, {}, {}, {})
    with pytest.raises(ValueError):
        evaluate_context_reuse([row])


def test_rejects_unknown_outcome():
    with pytest.raises(ValueError):
        evaluate_context_reuse([_row("X", {"billnyay": {"cached": 1}}, {}, {}, {})])
