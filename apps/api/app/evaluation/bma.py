"""
BMA — Benchmark Mapping Accuracy.

Does a hospital bill line resolve to the right CGHS reference rate key? Scored on the
production matcher (``billnyay`` endpoint ``_match_cghs_key``), SYNTHETIC dataset
``data/evaluation/bma_synthetic.jsonl``.

For every row: gold = acceptable keys (``[]`` = no counterpart exists), predicted = the
key the matcher returns (or None).

- ``correct``      predicted key in gold, or both are "no counterpart"
- ``wrong_key``    gold has keys but the matcher returned a different one (a wrong rate would
                   be applied — the costly error)
- ``missed``       gold has keys, matcher returned None (line left un-benchmarked — safe)
- ``false_match``  gold is empty but the matcher returned a key (an unrelated rate applied)
"""

import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from app.evaluation.metrics import accuracy, precision_recall_f1

logger = logging.getLogger("arogyarakshak.evaluation.bma")

Matcher = Callable[[str], Optional[str]]


def classify(expected_keys: List[str], predicted: Optional[str]) -> str:
    if not expected_keys:
        return "correct" if predicted is None else "false_match"
    if predicted is None:
        return "missed"
    return "correct" if predicted in expected_keys else "wrong_key"


def evaluate_bma(rows: List[Dict[str, Any]], matcher: Matcher) -> Dict[str, Any]:
    outcomes: Dict[str, int] = defaultdict(int)
    per_category: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    failures: List[Dict[str, Any]] = []
    tp = fp = fn = 0
    for row in rows:
        predicted = matcher(row["hospital_line"].lower().strip())
        outcome = classify(row["expected_keys"], predicted)
        outcomes[outcome] += 1
        per_category[row["category"]][outcome] += 1
        per_category[row["category"]]["n"] += 1
        has_gold = bool(row["expected_keys"])
        if predicted is not None and outcome == "correct":
            tp += 1
        elif predicted is not None:
            fp += 1
        if has_gold and outcome != "correct":
            fn += 1
        if outcome != "correct":
            failures.append(
                {"id": row["id"], "line": row["hospital_line"], "outcome": outcome,
                 "expected": row["expected_keys"], "predicted": predicted}
            )
    n = len(rows)
    logger.info("BMA evaluated %d rows: %s", n, dict(outcomes))
    return {
        "metric": "BMA",
        "rows": n,
        "accuracy": accuracy(outcomes["correct"], n),
        "outcomes": {k: outcomes.get(k, 0) for k in ("correct", "wrong_key", "missed", "false_match")},
        "mapping": precision_recall_f1(tp, fp, fn),
        "per_category": {c: dict(v) for c, v in per_category.items()},
        "failures": failures,
    }
