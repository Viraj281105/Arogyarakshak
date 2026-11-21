"""Retrieval harness: metrics checked against tiny hand-computed cases, then dataset structure
(synthetic flag, tuning/held-out flags, every gold clause exists in the corpus, the corpus still
equals what the source modules produce), a smoke floor, and that the committed results JSON is
exactly what the code regenerates. The smoke floor is NOT an accuracy claim."""

import json
from types import SimpleNamespace

import pytest

from app.evaluation import retrieval as R
from app.evaluation.datasets import DATA_DIR, DatasetError, load_dataset
from app.evaluation.retrieval import (
    OVERFETCH,
    build_bm25_searcher,
    build_results,
    evaluate_retrieval,
    evaluate_retrieval_dataset,
)
from app.evaluation.retrieval_corpus import CORPUS_META, build_corpus_rows


def H(source, page=1):
    return SimpleNamespace(source=source, page=page, quote="q", score=1.0)


def _searcher(table):
    return lambda query, k: table[query][:k]


# Chosen so recall, micro_recall, precision, mrr, hit_rate and f1 all differ at k=3.
GOLD = [
    {"id": "Q1", "query": "q1", "relevant": ["A#1", "B#1"]},
    {"id": "Q2", "query": "q2", "relevant": ["C#1"]},
    {"id": "Q3", "query": "q3", "relevant": ["D#1", "E#1", "F#1", "G#1"]},
    {"id": "Q4", "query": "q4", "relevant": ["H#1"]},
    {"id": "Q5", "query": "q5", "relevant": []},
]
RETURNS = {
    "q1": [H("A"), H("X"), H("B")],
    "q2": [H("Y"), H("Z"), H("C")],
    "q3": [H("D")],
    "q4": [],
    "q5": [],
}


def test_metrics_hand_computed_with_every_metric_different():
    r = evaluate_retrieval(GOLD, _searcher(RETURNS), ks=(1, 3), headline_k=3)
    assert (r["queries"], r["answerable"], r["unanswerable"]) == (5, 4, 1)
    # reciprocal ranks: Q1 1, Q2 1/3, Q3 1, Q4 0 -> mean 7/12
    assert r["mrr"] == pytest.approx(7 / 12)
    k3 = r["at_k"]["3"]
    # per query @3: Q1 tp2 fp1 | Q2 tp1 fp2 | Q3 tp1 fn3 | Q4 fn1  -> tp4 fp3 fn4
    assert (k3["tp"], k3["fp"], k3["fn"]) == (4, 3, 4)
    assert k3["hit_rate"] == pytest.approx(3 / 4)
    assert k3["recall"] == pytest.approx((1 + 1 + 0.25 + 0) / 4)  # 0.5625
    assert k3["precision"] == pytest.approx(4 / 7)
    assert k3["micro_recall"] == pytest.approx(4 / 8)
    assert k3["f1"] == pytest.approx(2 * (4 / 7) * 0.5 / (4 / 7 + 0.5))
    assert k3["pcra"] == pytest.approx(4 / 8)  # correctly retrieved / total relevant (= micro recall)
    values = [k3["hit_rate"], k3["recall"], k3["precision"], k3["micro_recall"], k3["f1"], r["mrr"]]
    assert len({round(v, 6) for v in values}) == len(values)
    k1 = r["at_k"]["1"]
    assert (k1["tp"], k1["fp"], k1["fn"]) == (2, 1, 6)
    assert k1["hit_rate"] == pytest.approx(2 / 4)
    assert k1["recall"] == pytest.approx((0.5 + 0 + 0.25 + 0) / 4)
    assert r["pcra"] == k3["pcra"] and r["recall_at_k"] == k3["recall"] and r["precision"] == k3["precision"]
    assert r["abstention_rate"] == pytest.approx(1.0)


def test_miss_failure_record_is_complete():
    r = evaluate_retrieval(GOLD, _searcher(RETURNS), ks=(1, 3), headline_k=3)
    assert {"id": "Q4", "kind": "miss", "relevant": ["H#1"], "returned": []} in r["failures"]
    assert not any(f["id"] == "Q1" for f in r["failures"])


def test_returning_a_hit_for_an_unanswerable_query_is_a_false_positive_and_not_an_abstention():
    table = dict(RETURNS, q5=[H("Z")])
    r = evaluate_retrieval(GOLD, _searcher(table), ks=(3,), headline_k=3)
    assert r["abstention_rate"] == pytest.approx(0.0)
    assert r["at_k"]["3"]["fp"] == 4
    assert {"id": "Q5", "kind": "answered_out_of_corpus", "returned": ["Z#1"]} in r["failures"]


def test_duplicate_hits_from_one_clause_count_once_and_do_not_push_the_rank():
    gold = [{"id": "G", "query": "q", "relevant": ["A#1"]}]
    table = {"q": [H("X"), H("X"), H("X"), H("A")]}
    r = evaluate_retrieval(gold, _searcher(table), ks=(3,), headline_k=3)
    assert r["mrr"] == pytest.approx(1 / 2)  # X counted once, A is rank 2
    k3 = r["at_k"]["3"]
    assert (k3["tp"], k3["fp"], k3["fn"]) == (1, 1, 0)


def test_page_distinguishes_clauses():
    gold = [{"id": "G", "query": "q", "relevant": ["A#2"]}]
    r = evaluate_retrieval(gold, _searcher({"q": [H("A", 1), H("A", 2)]}), ks=(1, 3), headline_k=3)
    assert r["mrr"] == pytest.approx(0.5)
    assert r["at_k"]["1"]["hit_rate"] == 0.0 and r["at_k"]["3"]["hit_rate"] == 1.0


def test_searcher_is_overfetched_once_per_query():
    calls = []

    def searcher(query, k):
        calls.append((query, k))
        return []

    evaluate_retrieval(GOLD[:2], searcher, ks=(1, 3, 5), headline_k=3)
    assert calls == [("q1", 5 * OVERFETCH), ("q2", 5 * OVERFETCH)]


def test_overfetch_keeps_recall_from_being_undercounted_by_chunk_duplicates():
    gold = [{"id": "G", "query": "q", "relevant": ["B#1"]}]
    table = {"q": [H("A"), H("A"), H("A"), H("B")]}  # three chunks of one passage, then the relevant one
    r = evaluate_retrieval(gold, _searcher(table), ks=(1, 3), headline_k=3)
    assert r["at_k"]["3"]["hit_rate"] == 1.0 and r["mrr"] == pytest.approx(0.5)


def test_undefined_metrics_are_none_not_zero():
    r = evaluate_retrieval([{"id": "U", "query": "q", "relevant": []}], _searcher({"q": []}), ks=(3,), headline_k=3)
    assert r["answerable"] == 0
    assert r["mrr"] is None and r["pcra"] is None and r["abstention_rate"] == 1.0


def test_empty_gold_rows_give_none_everywhere():
    r = evaluate_retrieval([], _searcher({}), ks=(1, 3), headline_k=3)
    assert r["queries"] == 0 and r["failures"] == []
    assert r["mrr"] is None and r["pcra"] is None and r["precision"] is None and r["abstention_rate"] is None
    assert r["at_k"]["3"]["hit_rate"] is None


def test_headline_k_must_be_one_of_ks():
    with pytest.raises(ValueError):
        evaluate_retrieval(GOLD, _searcher(RETURNS), ks=(1, 5), headline_k=3)


# ---- datasets ----------------------------------------------------------------
def _load():
    cmeta, corpus = load_dataset(DATA_DIR / R.CORPUS_FILE)
    tmeta, tuning = load_dataset(DATA_DIR / R.TUNING_FILE)
    hmeta, heldout = load_dataset(DATA_DIR / R.HELDOUT_FILE)
    return cmeta, corpus, tmeta, tuning, hmeta, heldout


def test_datasets_are_flagged_synthetic_with_tuning_and_heldout_marked():
    cmeta, corpus, tmeta, tuning, hmeta, heldout = _load()
    assert all(m["synthetic"] is True for m in (cmeta, tmeta, hmeta))
    assert tmeta["tuning"] is True and hmeta["tuning"] is False and hmeta["heldout"] is True
    assert len(tuning) >= 40 and len(heldout) >= 20 and len(corpus) >= 20
    assert not {r["id"] for r in tuning} & {r["id"] for r in heldout}
    assert not {r["query"] for r in tuning} & {r["query"] for r in heldout}
    for rows in (tuning, heldout):
        assert sum(1 for g in rows if not g["relevant"]) >= 5
    assert {g["group"] for g in tuning} >= {"paraphrase", "out_of_corpus"}


def test_every_gold_clause_exists_in_the_corpus():
    _c, corpus, _t, tuning, _h, heldout = _load()
    keys = {f"{c['source']}#{c['page']}" for c in corpus}
    assert len(keys) == len(corpus)
    for g in tuning + heldout:
        for rel in g["relevant"]:
            assert rel in keys, (g["id"], rel)
        assert len(set(g["relevant"])) == len(g["relevant"])


def test_corpus_file_still_equals_what_the_source_modules_produce():
    """Drift detection: if SchemeSetu/BimaNyay/DaaviSetu wording changes, regenerate with
    `python -m app.evaluation.retrieval_corpus` and re-check the labels in the queries files."""
    cmeta, corpus, *_ = _load()
    assert cmeta == CORPUS_META
    assert corpus == build_corpus_rows()


def test_loader_refuses_an_unflagged_dataset(tmp_path):
    p = tmp_path / "retrieval_x.jsonl"
    p.write_text('{"_meta": {"name": "x"}}\n{"id": "1"}\n', encoding="utf-8")
    with pytest.raises(DatasetError):
        load_dataset(p)


def test_searcher_is_deterministic_over_every_group_and_quotes_are_corpus_text():
    _c, corpus, _t, tuning, _h, heldout = _load()
    search = build_bm25_searcher(corpus)
    texts = {f"{c['source']}#{c['page']}": c["text"] for c in corpus}
    for g in tuning + heldout:
        first = search(g["query"], 3)
        assert [(h.source, h.page, h.score) for h in first] == [(h.source, h.page, h.score) for h in search(g["query"], 3)]
        for h in first:
            assert h.quote in texts[f"{h.source}#{h.page}"]


def test_smoke_floor_a_retriever_returning_nothing_fails_it():
    """A loose smoke test (not an accuracy claim): the retriever must find SOMETHING relevant for a
    clear majority of answerable queries, and the harness must be able to tell it apart from a
    retriever that returns nothing."""
    _c, corpus, _t, tuning, _h, heldout = _load()
    empty = evaluate_retrieval(tuning, lambda q, k: [])
    assert empty["at_k"]["3"]["hit_rate"] == 0.0
    for rows in (tuning, heldout):
        r = evaluate_retrieval_dataset(corpus, rows)
        assert r["queries"] == len(rows) and r["answerable"] + r["unanswerable"] == len(rows)
        assert r["at_k"]["3"]["hit_rate"] > 0.5, "retriever smoke floor"
        assert r["mrr"] > 0.4
        assert r["abstention_rate"] >= 0.5  # abstaining on everything is not enough: see hit_rate


def test_parameters_are_plumbed_through_the_dataset_wrapper():
    _c, corpus, _t, tuning, *_ = _load()
    default = evaluate_retrieval_dataset(corpus, tuning)
    loose = evaluate_retrieval_dataset(corpus, tuning, min_coverage=0.0)
    strict = evaluate_retrieval_dataset(corpus, tuning, min_coverage=1.0)
    assert loose["abstention_rate"] < default["abstention_rate"] <= strict["abstention_rate"]
    assert strict["at_k"]["3"]["hit_rate"] < default["at_k"]["3"]["hit_rate"] < loose["at_k"]["3"]["hit_rate"]
    huge_floor = evaluate_retrieval_dataset(corpus, tuning, min_score=1e9)
    assert huge_floor["at_k"]["3"]["hit_rate"] == 0.0
    ratio = evaluate_retrieval_dataset(corpus, tuning, min_score_ratio=0.99)
    assert ratio["at_k"]["3"]["hit_rate"] < default["at_k"]["3"]["hit_rate"]


def test_committed_results_json_is_exactly_what_the_code_regenerates():
    """docs/evaluation/retrieval_results.json is the source of every figure in
    docs/evaluation/retrieval.md. Regenerate: `python -m app.evaluation.retrieval` (from apps/api)."""
    committed = json.loads(R.RESULTS_PATH.read_text(encoding="utf-8"))
    assert committed == build_results()


def test_results_json_sweeps_contain_the_defaults_row_matching_the_headline():
    results = json.loads(R.RESULTS_PATH.read_text(encoding="utf-8"))
    d = results["defaults"]
    for param in ("min_coverage", "min_score_ratio", "min_score"):
        row = next(r for r in results["sweeps"][param] if r["value"] == d[param])
        assert row["tuning"]["mrr"] == results["tuning"]["mrr"]
        assert row["heldout"]["abstention_rate"] == results["heldout"]["abstention_rate"]
