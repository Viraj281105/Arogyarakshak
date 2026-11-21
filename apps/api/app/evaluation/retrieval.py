"""
Retrieval harness — Recall@k, MRR, precision/recall and PCRA for clause retrieval.

Scores ``kadi.retrieval`` (BM25) on HAND-LABELLED, SYNTHETIC gold sets built on clean,
in-repo text (``data/evaluation/retrieval_corpus_synthetic.jsonl`` and
``retrieval_queries_synthetic.jsonl``). The real downloaded Marathi/Hindi PDFs have corrupted
text layers and are not used. The numbers describe how the retriever behaves on these
queries, which were written by the same team that wrote the retriever; they are not
real-world retrieval accuracy.

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
with an empty list.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Sequence

from app.evaluation.metrics import precision_recall_f1, safe_div

logger = logging.getLogger("arogyarakshak.evaluation.retrieval")

Searcher = Callable[[str, int], Sequence[Any]]  # (query, k) -> hits with .source and .page

DEFAULT_KS = (1, 3, 5)
DEFAULT_HEADLINE_K = 3


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
        retrieved = _dedupe(searcher(row["query"], k_max))[:k_max]
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


def build_bm25_searcher(corpus_rows: List[Dict[str, Any]], min_score: Optional[float] = None) -> Searcher:
    """A searcher over a fresh in-memory ``kadi.retrieval`` index of the corpus rows
    (``{"source", "page", "text"}``). Nothing is written to disk."""
    from kadi.retrieval import DEFAULT_MIN_SCORE, CaseRetrievalIndex

    index = CaseRetrievalIndex("evaluation", min_score=DEFAULT_MIN_SCORE if min_score is None else min_score)
    for row in corpus_rows:
        index.add_document(row["text"], source=row["source"], page=row["page"])
    return index.search


def evaluate_retrieval_dataset(
    corpus_rows: List[Dict[str, Any]],
    gold_rows: List[Dict[str, Any]],
    min_score: Optional[float] = None,
    ks: Sequence[int] = DEFAULT_KS,
    headline_k: int = DEFAULT_HEADLINE_K,
) -> Dict[str, Any]:
    """Convenience wrapper the runner uses: build the BM25 searcher, then score it."""
    return evaluate_retrieval(gold_rows, build_bm25_searcher(corpus_rows, min_score), ks=ks, headline_k=headline_k)
