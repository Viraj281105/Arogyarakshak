"""
Retrieval harness — Recall@k, MRR, precision/recall and PCRA for clause retrieval.

Scores ``kadi.retrieval`` (BM25) on HAND-LABELLED, SYNTHETIC gold sets built on clean,
in-repo text (``data/evaluation/retrieval_corpus_synthetic.jsonl``, the tuning queries in
``retrieval_queries_synthetic.jsonl`` and the held-out slice ``retrieval_heldout_synthetic.jsonl``).
The real downloaded Marathi/Hindi PDFs have corrupted text layers and are not used. The labels
were written by the same author as the retriever; the numbers describe how the retriever behaves
on these queries, not real-world retrieval accuracy. The tuning set is the one the retriever's
floors were chosen on, so its figures are optimistic; the held-out slice is reported separately.

A gold row is ``{"id", "query", "relevant": ["<source>#<page>", ...]}``; an empty
``relevant`` marks an out-of-corpus query that must return NOTHING (never a guess).
Per cut ``k``:

- ``hit_rate``   share of answerable queries with at least one relevant clause in the top k
- ``recall``     mean over answerable queries of (relevant found in top k / relevant)
- precision / micro_recall: micro-averaged over all queries (a hit returned for an
  out-of-corpus query is a false positive); duplicates of one clause count once
- ``pcra``       Precision of Correct Retrieved clauses: correctly retrieved relevant clauses
  divided by the total relevant clauses (equal to micro_recall; reported under both names)

``mrr`` is the mean reciprocal rank of the first relevant clause (0 when none is returned),
over answerable queries. ``abstention_rate`` is the share of out-of-corpus queries answered
with an empty list. The searcher is asked for ``OVERFETCH`` times the largest cut so that
several chunks of one passage cannot push other passages out before de-duplication.

``build_results()`` regenerates every figure quoted in ``docs/evaluation/retrieval.md`` (defaults,
both query sets and the sensitivity sweeps); ``docs/evaluation/retrieval_results.json`` is its
committed output and a test fails when they differ. Regenerate from ``apps/api`` with
``python -m app.evaluation.retrieval``.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from app.evaluation.datasets import DATA_DIR, load_dataset
from app.evaluation.metrics import precision_recall_f1, safe_div

logger = logging.getLogger("arogyarakshak.evaluation.retrieval")

Searcher = Callable[[str, int], Sequence[Any]]  # (query, k) -> hits with .source and .page

DEFAULT_KS = (1, 3, 5)
DEFAULT_HEADLINE_K = 3
OVERFETCH = 5
RESULTS_PATH = Path(__file__).resolve().parents[4] / "docs" / "evaluation" / "retrieval_results.json"
CORPUS_FILE = "retrieval_corpus_synthetic.jsonl"
TUNING_FILE = "retrieval_queries_synthetic.jsonl"
HELDOUT_FILE = "retrieval_heldout_synthetic.jsonl"


def _key(hit: Any) -> str:
    return f"{hit.source}#{hit.page}"


def _dedupe(hits: Sequence[Any]) -> List[str]:
    return list(dict.fromkeys(_key(h) for h in hits))


def evaluate_retrieval(
    gold_rows: List[Dict[str, Any]],
    searcher: Searcher,
    ks: Sequence[int] = DEFAULT_KS,
    headline_k: int = DEFAULT_HEADLINE_K,
) -> Dict[str, Any]:
    ks = tuple(sorted(set(ks)))
    if headline_k not in ks:
        raise ValueError("headline_k must be one of ks")
    k_max = ks[-1]

    answerable = unanswerable = abstained = 0
    rr_sum = 0.0
    per_k = {k: {"tp": 0, "fp": 0, "fn": 0, "hit": 0, "recall_sum": 0.0, "relevant": 0} for k in ks}
    failures: List[Dict[str, Any]] = []

    for row in gold_rows:
        relevant = list(dict.fromkeys(row["relevant"]))
        retrieved = _dedupe(searcher(row["query"], k_max * OVERFETCH))[:k_max]
        if not relevant:
            unanswerable += 1
            abstained += not retrieved
            for k in ks:
                per_k[k]["fp"] += len(retrieved[:k])
            if retrieved:
                failures.append({"id": row["id"], "kind": "answered_out_of_corpus", "returned": retrieved[:headline_k]})
            continue
        answerable += 1
        rank = next((i for i, key in enumerate(retrieved, 1) if key in relevant), None)
        rr_sum += 1 / rank if rank else 0.0
        for k in ks:
            top = retrieved[:k]
            found = [r for r in relevant if r in top]
            c = per_k[k]
            c["tp"] += len(found)
            c["fp"] += len(top) - len(found)
            c["fn"] += len(relevant) - len(found)
            c["hit"] += bool(found)
            c["recall_sum"] += len(found) / len(relevant)
            c["relevant"] += len(relevant)
        head = retrieved[:headline_k]
        if not any(r in head for r in relevant):
            failures.append({"id": row["id"], "kind": "miss", "relevant": relevant, "returned": head})

    at_k: Dict[str, Dict[str, Optional[float]]] = {}
    for k in ks:
        c = per_k[k]
        prf = precision_recall_f1(c["tp"], c["fp"], c["fn"])
        at_k[str(k)] = {
            "hit_rate": safe_div(c["hit"], answerable),
            "recall": safe_div(c["recall_sum"], answerable),
            "precision": prf["precision"],
            "micro_recall": prf["recall"],
            "f1": prf["f1"],
            "pcra": safe_div(c["tp"], c["relevant"]),
            "tp": c["tp"],
            "fp": c["fp"],
            "fn": c["fn"],
        }
    head_metrics = at_k[str(headline_k)]
    logger.info("retrieval evaluated %d queries (%d answerable)", len(gold_rows), answerable)
    return {
        "metric": "retrieval",
        "queries": len(gold_rows),
        "answerable": answerable,
        "unanswerable": unanswerable,
        "headline_k": headline_k,
        "mrr": safe_div(rr_sum, answerable),
        "recall_at_k": head_metrics["recall"],
        "pcra": head_metrics["pcra"],
        "precision": head_metrics["precision"],
        "abstention_rate": safe_div(abstained, unanswerable),
        "at_k": at_k,
        "failures": failures,
    }


def build_bm25_searcher(
    corpus_rows: List[Dict[str, Any]],
    min_score: Optional[float] = None,
    min_coverage: Optional[float] = None,
    min_score_ratio: Optional[float] = None,
) -> Searcher:
    """A searcher over a fresh in-memory ``kadi.retrieval`` index of the corpus rows
    (``{"source", "page", "text"}``). ``None`` keeps that parameter's library default. Nothing
    is written to disk."""
    from kadi.retrieval import CaseRetrievalIndex

    options = {
        name: value
        for name, value in (("min_score", min_score), ("min_coverage", min_coverage), ("min_score_ratio", min_score_ratio))
        if value is not None
    }
    index = CaseRetrievalIndex("evaluation", **options)
    for row in corpus_rows:
        index.add_document(row["text"], source=row["source"], page=row["page"])
    return index.search


def evaluate_retrieval_dataset(
    corpus_rows: List[Dict[str, Any]],
    gold_rows: List[Dict[str, Any]],
    min_score: Optional[float] = None,
    min_coverage: Optional[float] = None,
    min_score_ratio: Optional[float] = None,
    ks: Sequence[int] = DEFAULT_KS,
    headline_k: int = DEFAULT_HEADLINE_K,
) -> Dict[str, Any]:
    """Convenience wrapper the runner uses: build the BM25 searcher, then score it."""
    searcher = build_bm25_searcher(corpus_rows, min_score, min_coverage, min_score_ratio)
    return evaluate_retrieval(gold_rows, searcher, ks=ks, headline_k=headline_k)


# ---- reproducible results -----------------------------------------------------
_SUMMARY_KEYS = ("queries", "answerable", "unanswerable", "mrr", "recall_at_k", "pcra", "precision", "abstention_rate")
SWEEPS = {
    "min_coverage": [0.0, 0.34, 0.5, 0.67, 1.0],
    "min_score_ratio": [0.0, 0.1, 0.25, 0.5, 0.75],
    "min_score": [0.0, 0.5, 1.0, 2.0],
}


def _round(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {k: _round(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_round(v) for v in value]
    return value


def _summary(report: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: report[k] for k in _SUMMARY_KEYS}
    out["hit_rate_at_1"] = report["at_k"]["1"]["hit_rate"]
    out["hit_rate_at_3"] = report["at_k"]["3"]["hit_rate"]
    out["hit_rate_at_5"] = report["at_k"]["5"]["hit_rate"]
    return out


def build_results() -> Dict[str, Any]:
    """Every figure quoted in docs/evaluation/retrieval.md, regenerated from the datasets."""
    c_meta, corpus = load_dataset(DATA_DIR / CORPUS_FILE)
    t_meta, tuning = load_dataset(DATA_DIR / TUNING_FILE)
    h_meta, heldout = load_dataset(DATA_DIR / HELDOUT_FILE)
    from kadi.retrieval import DEFAULT_MIN_COVERAGE, DEFAULT_MIN_SCORE, DEFAULT_MIN_SCORE_RATIO

    defaults = {
        "min_score": DEFAULT_MIN_SCORE,
        "min_coverage": DEFAULT_MIN_COVERAGE,
        "min_score_ratio": DEFAULT_MIN_SCORE_RATIO,
    }
    tuning_report = evaluate_retrieval_dataset(corpus, tuning)
    heldout_report = evaluate_retrieval_dataset(corpus, heldout)
    sweeps: Dict[str, List[Dict[str, Any]]] = {}
    for param, values in SWEEPS.items():
        rows = []
        for value in values:
            row: Dict[str, Any] = {"value": value}
            for name, rows_set in (("tuning", tuning), ("heldout", heldout)):
                report = evaluate_retrieval_dataset(corpus, rows_set, **{param: value})
                row[name] = {
                    "mrr": report["mrr"],
                    "hit_rate_at_3": report["at_k"]["3"]["hit_rate"],
                    "pcra": report["pcra"],
                    "precision": report["precision"],
                    "abstention_rate": report["abstention_rate"],
                }
            rows.append(row)
        sweeps[param] = rows
    result = {
        "note": (
            "SYNTHETIC hand-labelled sets written by the retriever's author. 'tuning' is the set the floors were "
            "chosen on (optimistic); 'heldout' is reported separately. Not real-world accuracy."
        ),
        "corpus_passages": len(corpus),
        "corpus_meta_name": c_meta["name"],
        "defaults": defaults,
        "tuning": {"meta_name": t_meta["name"], **_summary(tuning_report), "failures": tuning_report["failures"]},
        "heldout": {"meta_name": h_meta["name"], **_summary(heldout_report), "failures": heldout_report["failures"]},
        "sweeps": sweeps,
    }
    return _round(result)


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS_PATH
    target.write_text(json.dumps(build_results(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {target}")
