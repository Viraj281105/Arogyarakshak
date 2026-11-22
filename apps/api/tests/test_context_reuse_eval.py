"""#112: context hit rate / DPR scorer, with hand-computed expectations."""

import pytest

from app.evaluation.context_reuse import evaluate_context_reuse


def _row(sid, documents, ingest, requests):
    return {"id": sid, "documents": documents, "ingest": ingest, "requests": requests}


# 2 documents, ingest 2 OCR + 2 extraction = 4 units, 6 requests (5 served, 1 empty).
# current = 4; baseline = 4 + 6 requests x 2 documents x 2 units = 28; DPR = 24 / 28.
S1 = _row("S1", 2, {"ocr": 2, "extraction": 2},
          {"billnyay": {"served": 3, "empty": 1}, "dawacheck": {"served": 2}})
# 1 document, ingest 2 units, 2 requests, none served: current 2; baseline 2 + 2 x 1 x 2 = 6; DPR = 4 / 6.
S2 = _row("S2", 1, {"ocr": 1, "extraction": 1}, {"schemesetu": {"empty": 2}})


def test_single_scenario_hand_computed():
    r = evaluate_context_reuse([S1])
    assert (r["n_scenarios"], r["n_requests"], r["served"]) == (1, 6, 5)
    assert r["hit_rate"] == round(5 / 6, 4)
    assert (r["current_work"], r["baseline_work"]) == (4, 28)
    assert r["dpr"] == round(24 / 28, 4)
    assert r["per_module_hit_rate"] == {"billnyay": 0.75, "dawacheck": 1.0}


def test_two_scenarios_are_pooled_not_averaged():
    r = evaluate_context_reuse([S1, S2])
    assert (r["n_requests"], r["served"]) == (8, 5)
    assert r["hit_rate"] == round(5 / 8, 4)           # pooled; the mean of 0.8333 and 0 would be 0.4167
    assert (r["current_work"], r["baseline_work"]) == (6, 34)
    assert r["dpr"] == round(28 / 34, 4)              # pooled; the mean of 0.8571 and 0.6667 would differ
    assert [s["hit_rate"] for s in r["per_scenario"]] == [round(5 / 6, 4), 0.0]
    assert r["per_scenario"][1]["dpr"] == round(4 / 6, 4)


def test_no_requests_means_no_savings_and_undefined_rate():
    r = evaluate_context_reuse([_row("N", 1, {"ocr": 1, "extraction": 1}, {})])
    assert r["dpr"] == 0.0 and r["hit_rate"] is None  # nothing read: hit rate undefined, never 0 or 1
    empty = evaluate_context_reuse([_row("E", 0, {}, {})])
    assert empty["dpr"] is None and empty["hit_rate"] is None
    assert evaluate_context_reuse([])["dpr"] is None


@pytest.mark.parametrize("bad", [-1, 1.5, True, "3"])
def test_rejects_invalid_counts(bad):
    with pytest.raises(ValueError):
        evaluate_context_reuse([_row("X", 1, {}, {"billnyay": {"served": bad}})])
    with pytest.raises(ValueError):
        evaluate_context_reuse([_row("X", bad, {}, {})])


def test_rejects_unknown_outcome():
    with pytest.raises(ValueError):
        evaluate_context_reuse([_row("X", 1, {}, {"billnyay": {"reused": 1}})])
