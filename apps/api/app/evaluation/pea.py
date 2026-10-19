"""
PEA — Procedure Extraction Accuracy.

Scores Kadi's offline heuristic bill extractor (``run_heuristic_extraction_fallback`` — the
path used when no Groq key is configured; the LLM path is NOT measured here) on SYNTHETIC
mock bills (``data/evaluation/pea_synthetic.jsonl``).

A predicted line item is correct only if BOTH its name (case-insensitive, whitespace
collapsed) and its amount equal a gold item. Reported:

- procedure-line precision / recall / F1 (multiset comparison)
- medicine-line precision / recall / F1
- all-items F1 ignoring the procedure/medicine split, and ``split_errors`` (items found with
  the right name+amount but filed under the wrong list)
- total-amount accuracy (stated grand total extracted exactly)
"""

import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Tuple

from app.evaluation.metrics import accuracy, multiset_match_counts, precision_recall_f1

logger = logging.getLogger("arogyarakshak.evaluation.pea")

Extractor = Callable[[str], Any]  # text -> object with .procedures / .medicines / .total_amount


def _key(name: str, amount: float) -> Tuple[str, float]:
    return (" ".join(str(name).lower().split()), round(float(amount), 2))


def _pred_items(extracted: Any) -> Tuple[List[Tuple[str, float]], List[Tuple[str, float]]]:
    procs = [_key(p["name"], p["amount"]) for p in extracted.procedures]
    meds = [_key(m["name"], m["cost"]) for m in extracted.medicines]
    return procs, meds


def evaluate_pea(rows: List[Dict[str, Any]], extractor: Extractor) -> Dict[str, Any]:
    totals = {k: defaultdict(int) for k in ("procedures", "medicines", "all")}
    per_category: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total_correct = 0
    split_errors = 0
    failures: List[Dict[str, Any]] = []
    for row in rows:
        extracted = extractor(row["text"])
        pred_p, pred_m = _pred_items(extracted)
        gold_p = [_key(n, a) for n, a in row["procedures"]]
        gold_m = [_key(n, a) for n, a in row["medicines"]]
        counts = {
            "procedures": multiset_match_counts(gold_p, pred_p),
            "medicines": multiset_match_counts(gold_m, pred_m),
            "all": multiset_match_counts(gold_p + gold_m, pred_p + pred_m),
        }
        for name, c in counts.items():
            for k, v in c.items():
                totals[name][k] += v
        # items correct as (name, amount) overall but filed in the wrong list
        split = counts["all"]["tp"] - counts["procedures"]["tp"] - counts["medicines"]["tp"]
        split_errors += split
        for k in ("tp", "fp", "fn"):
            per_category[row["category"]][k] += counts["all"][k]
        per_category[row["category"]]["bills"] += 1
        total_ok = abs(float(extracted.total_amount) - float(row["total_amount"])) < 0.005
        total_correct += total_ok
        if counts["all"]["fp"] or counts["all"]["fn"] or split or not total_ok:
            failures.append(
                {"id": row["id"], "category": row["category"], "gold_procedures": gold_p, "pred_procedures": pred_p,
                 "gold_medicines": gold_m, "pred_medicines": pred_m, "total_ok": total_ok,
                 "split_errors": split}
            )
    n = len(rows)
    logger.info("PEA evaluated %d bills (%d with any error)", n, len(failures))
    return {
        "metric": "PEA",
        "bills": n,
        "gold_procedures": totals["procedures"]["tp"] + totals["procedures"]["fn"],
        "gold_medicines": totals["medicines"]["tp"] + totals["medicines"]["fn"],
        "procedures": {**dict(totals["procedures"]), **precision_recall_f1(*(totals["procedures"][k] for k in ("tp", "fp", "fn")))},
        "medicines": {**dict(totals["medicines"]), **precision_recall_f1(*(totals["medicines"][k] for k in ("tp", "fp", "fn")))},
        "all_items": {**dict(totals["all"]), **precision_recall_f1(*(totals["all"][k] for k in ("tp", "fp", "fn")))},
        "split_errors": split_errors,
        "total_amount_accuracy": accuracy(total_correct, n),
        "per_category": {c: dict(v) for c, v in per_category.items()},
        "bills_with_errors": len(failures),
        "failures": failures,
    }
