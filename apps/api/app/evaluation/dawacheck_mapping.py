"""
DawaCheck price-mapping accuracy.

Does a medicine name resolve to the right entry of DawaCheck's curated NPPA reference subset
(and so to the right per-unit ceiling price)? Scored on ``benchmark_medicine`` with a
SYNTHETIC dataset (``data/evaluation/dawacheck_mapping_synthetic.jsonl``). The reference
table has only 7 formulations, so most of what this measures is matching behaviour on that
tiny table — never coverage of the real NPPA schedule.

- ``correct``      mapped to the expected formulation, or correctly left unmapped
- ``wrong_drug``   mapped to a different formulation than expected (a wrong ceiling applies)
- ``false_match``  expected unmapped (not in subset) but a formulation was returned
- ``missed``       expected a formulation, got None (safe: nothing is asserted)
- ``ceiling_accuracy``  among correctly mapped rows with a gold ceiling, share whose
                        returned per-unit ceiling is within ₹0.01 of the gold value
"""

import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from app.evaluation.metrics import accuracy, precision_recall_f1

logger = logging.getLogger("arogyarakshak.evaluation.dawacheck")

Mapper = Callable[[str], Optional[Any]]  # query -> object with .active_ingredient / .nppa_ceiling_price / .match_method


def classify(expected: Optional[str], got: Optional[str]) -> str:
    if expected is None:
        return "correct" if got is None else "false_match"
    if got is None:
        return "missed"
    return "correct" if got == expected else "wrong_drug"


def evaluate_dawacheck_mapping(rows: List[Dict[str, Any]], mapper: Mapper) -> Dict[str, Any]:
    outcomes: Dict[str, int] = defaultdict(int)
    per_category: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    methods: Dict[str, int] = defaultdict(int)
    tp = fp = fn = 0
    ceiling_total = ceiling_ok = 0
    failures: List[Dict[str, Any]] = []
    for row in rows:
        got = mapper(row["query"])
        got_name = got.active_ingredient if got is not None else None
        outcome = classify(row["expected_active_ingredient"], got_name)
        outcomes[outcome] += 1
        per_category[row["category"]][outcome] += 1
        per_category[row["category"]]["n"] += 1
        if got is not None:
            methods[got.match_method] += 1
        if got_name is not None and outcome == "correct":
            tp += 1
        elif got_name is not None:
            fp += 1
        if row["expected_active_ingredient"] is not None and outcome != "correct":
            fn += 1
        ceiling_note = None
        if outcome == "correct" and got is not None and row.get("expected_ceiling") is not None:
            ceiling_total += 1
            ok = abs(float(got.nppa_ceiling_price) - float(row["expected_ceiling"])) <= 0.01
            ceiling_ok += ok
            if not ok:
                ceiling_note = {"expected_ceiling": row["expected_ceiling"], "got_ceiling": got.nppa_ceiling_price}
        if outcome != "correct" or ceiling_note:
            failures.append(
                {"id": row["id"], "query": row["query"], "outcome": outcome if outcome != "correct" else "ceiling_mismatch",
                 "expected": row["expected_active_ingredient"], "got": got_name,
                 "match_method": got.match_method if got is not None else None, **(ceiling_note or {})}
            )
    n = len(rows)
    logger.info("DawaCheck mapping evaluated %d rows: %s", n, dict(outcomes))
    return {
        "metric": "dawacheck_price_mapping",
        "rows": n,
        "accuracy": accuracy(outcomes["correct"], n),
        "outcomes": {k: outcomes.get(k, 0) for k in ("correct", "wrong_drug", "false_match", "missed")},
        "mapping": precision_recall_f1(tp, fp, fn),
        "ceiling_checked": ceiling_total,
        "ceiling_accuracy": accuracy(ceiling_ok, ceiling_total),
        "match_methods_returned": dict(methods),
        "per_category": {c: dict(v) for c, v in per_category.items()},
        "failures": failures,
    }
