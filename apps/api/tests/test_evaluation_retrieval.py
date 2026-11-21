"""Retrieval harness: metrics checked against tiny hand-computed cases, then dataset structure
(synthetic flag, n, ids, every gold clause exists in the corpus) and the BM25 searcher on the
hand-labelled clean in-repo corpus. The dataset tests assert structure and abstention
behaviour, never an accuracy figure."""

from types import SimpleNamespace

import pytest

from app.evaluation.datasets import DATA_DIR, DatasetError, load_dataset
from app.evaluation.retrieval import (
    build_bm25_searcher,
    evaluate_retrieval,
    evaluate_retrieval_dataset,
)


def H(source, page=1):
    return SimpleNamespace(source=source, page=page, quote="q", score=1.0)


GOLD = [
    {"id": "Q1", "query": "q1", "relevant": ["A#1"]},
    {"id": "Q2", "query": "q2", "relevant": ["C#1", "D#1"]},
    {"id": "Q3", "query": "q3", "relevant": ["E#1"]},
    {"id": "Q4", "query": "q4", "relevant": []},
]
RETURNS = {
    "q1": [H("A"), H("B")],
    "q2": [H("X"), H("C"), H("Y")],
    "q3": [],
    "q4": [],
}


def _searcher(table):
    return lambda query, k: table[query][:k]


def test_metrics_hand_computed():
    r = evaluate_retrieval(GOLD, _searcher(RETURNS), ks=(1, 3), headline_k=3)
    assert (r["queries"], r["answerable"], r["unanswerable"]) == (4, 3, 1)
    # reciprocal ranks: Q1 -> 1, Q2 -> 1/2, Q3 -> 0
    assert r["mrr"] == pytest.approx(0.5)
    k1, k3 = r["at_k"]["1"], r["at_k"]["3"]
    # @1: Q1 hits (A); Q2 returns X; Q3 nothing -> hit_rate 1/3, recall (1 + 0 + 0)/3
    assert k1["hit_rate"] == pytest.approx(1 / 3)
    assert k1["recall"] == pytest.approx(1 / 3)
    assert (k1["tp"], k1["fp"], k1["fn"]) == (1, 1, 3)  # fp: X; fn: Q2 misses 2, Q3 misses 1
    # @3: Q1 1/1, Q2 1/2, Q3 0/1 -> mean recall 0.5; hit rate 2/3
    assert k3["hit_rate"] == pytest.approx(2 / 3)
    assert k3["recall"] == pytest.approx(0.5)
    # micro counts: tp = 1 + 1 + 0 = 2; fp = 1 (B) + 2 (X, Y) = 3; fn = 0 + 1 (D) + 1 (E) = 2
    assert (k3["tp"], k3["fp"], k3["fn"]) == (2, 3, 2)
    assert k3["precision"] == pytest.approx(0.4)
    assert k3["micro_recall"] == pytest.approx(0.5)
    # PCRA = correctly retrieved relevant clauses / total relevant clauses = 2 / 4
    assert k3["pcra"] == pytest.approx(0.5)
    assert r["pcra"] == pytest.approx(0.5) and r["recall_at_k"] == pytest.approx(0.5)
    assert r["abstention_rate"] == pytest.approx(1.0)


def test_returning_a_hit_for_an_unanswerable_query_is_a_false_positive_and_not_an_abstention():
    table = dict(RETURNS, q4=[H("Z")])
    r = evaluate_retrieval(GOLD, _searcher(table), ks=(3,), headline_k=3)
    assert r["abstention_rate"] == pytest.approx(0.0)
    assert r["at_k"]["3"]["fp"] == 4  # B, X, Y, Z
    assert any(f["id"] == "Q4" for f in r["failures"])


def test_duplicate_hits_from_one_clause_count_once():
    table = {"q1": [H("A"), H("A"), H("A")]}
    r = evaluate_retrieval([GOLD[0]], _searcher(table), ks=(3,), headline_k=3)
    k3 = r["at_k"]["3"]
    assert (k3["tp"], k3["fp"], k3["fn"]) == (1, 0, 0)


def test_page_distinguishes_clauses():
    gold = [{"id": "G", "query": "q", "relevant": ["A#2"]}]
    r = evaluate_retrieval(gold, _searcher({"q": [H("A", 1), H("A", 2)]}), ks=(1, 3), headline_k=3)
    assert r["mrr"] == pytest.approx(0.5)
    assert r["at_k"]["1"]["hit_rate"] == 0.0 and r["at_k"]["3"]["hit_rate"] == 1.0


def test_searcher_is_asked_for_the_largest_k_only_once_per_query():
    calls = []

    def searcher(query, k):
        calls.append((query, k))
        return []

    evaluate_retrieval(GOLD[:2], searcher, ks=(1, 3, 5), headline_k=3)
    assert calls == [("q1", 5), ("q2", 5)]


def test_undefined_metrics_are_none_not_zero():
    r = evaluate_retrieval([{"id": "U", "query": "q", "relevant": []}], _searcher({"q": []}), ks=(3,), headline_k=3)
    assert r["answerable"] == 0
    assert r["mrr"] is None and r["pcra"] is None and r["abstention_rate"] == 1.0


def test_headline_k_must_be_one_of_ks():
    with pytest.raises(ValueError):
        evaluate_retrieval(GOLD, _searcher(RETURNS), ks=(1, 5), headline_k=3)


# ---- datasets ----------------------------------------------------------------
def _load():
    cmeta, corpus = load_dataset(DATA_DIR / "retrieval_corpus_synthetic.jsonl")
    qmeta, gold = load_dataset(DATA_DIR / "retrieval_queries_synthetic.jsonl")
    return cmeta, corpus, qmeta, gold


def test_datasets_are_flagged_synthetic_and_large_enough():
    cmeta, corpus, qmeta, gold = _load()
    assert cmeta["synthetic"] is True and qmeta["synthetic"] is True
    assert len(gold) >= 40
    assert sum(1 for g in gold if not g["relevant"]) >= 5  # out-of-corpus queries exist
    assert len(corpus) >= 20


def test_every_gold_clause_exists_in_the_corpus():
    _c, corpus, _q, gold = _load()
    keys = {f"{c['source']}#{c['page']}" for c in corpus}
    assert len(keys) == len(corpus)
    for g in gold:
        for rel in g["relevant"]:
            assert rel in keys, (g["id"], rel)


def test_loader_refuses_an_unflagged_dataset(tmp_path):
    p = tmp_path / "retrieval_x.jsonl"
    p.write_text('{"_meta": {"name": "x"}}\n{"id": "1"}\n', encoding="utf-8")
    with pytest.raises(DatasetError):
        load_dataset(p)


def test_searcher_over_the_corpus_is_deterministic_and_quotes_are_corpus_text():
    _c, corpus, _q, gold = _load()
    search = build_bm25_searcher(corpus)
    texts = {f"{c['source']}#{c['page']}": c["text"] for c in corpus}
    for g in gold[:10]:
        first = search(g["query"], 3)
        assert [(h.source, h.page) for h in first] == [(h.source, h.page) for h in search(g["query"], 3)]
        for h in first:
            assert h.quote in texts[f"{h.source}#{h.page}"]


def test_evaluate_dataset_end_to_end_reports_n_and_never_a_guess():
    _c, corpus, _q, gold = _load()
    r = evaluate_retrieval_dataset(corpus, gold)
    assert r["queries"] == len(gold) and r["answerable"] + r["unanswerable"] == len(gold)
    for key in ("mrr", "pcra", "abstention_rate", "at_k", "failures"):
        assert key in r
    # Out-of-corpus queries must come back empty rather than as a made-up citation.
    assert r["abstention_rate"] is not None and r["abstention_rate"] >= 0.8
