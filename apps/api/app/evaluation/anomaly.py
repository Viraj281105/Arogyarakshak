"""
Billing-anomaly precision / recall / F1.

Runs the production auditor (``audit_billing_lines``) over SYNTHETIC labelled bills
(``data/evaluation/billing_anomaly_synthetic.jsonl``). Positive class = a line that should
be flagged (``is_deviation``: overcharged, or a bundled item billed separately).

Line level: tp/fp/fn/tn per line. Bill level: a bill is anomalous when any line is.
False negatives are split into ``abstained`` (the auditor declined to compare — no CGHS
rate, or a per-day/visit rate with no stated count) and ``judged_fair`` (it compared and
found the charge acceptable), because abstaining is a deliberate safety behaviour with a
recall cost, not the same failure as a wrong verdict.
"""

import logging
from collections import defaultdict
from types import SimpleNamespace
from typing import Any, Callable, Dict, List

from app.evaluation.metrics import accuracy, binary_counts, precision_recall_f1

logger = logging.getLogger("arogyarakshak.evaluation.anomaly")

Auditor = Callable[[str, List[Any]], Any]  # (case_id, items) -> AuditResponse


def evaluate_anomaly(rows: List[Dict[str, Any]], auditor: Auditor) -> Dict[str, Any]:
    line_pairs = []
    bill_pairs = []
    fn_abstained = fn_fair = 0
    failures: List[Dict[str, Any]] = []
    per_category: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        items = [SimpleNamespace(name=l["name"], value=l["charged"]) for l in row["lines"]]
        result = auditor(row["id"], items)
        by_name = result.audit_items
        if len(by_name) != len(row["lines"]):
            raise ValueError(f"{row['id']}: auditor returned {len(by_name)} lines for {len(row['lines'])}")
        bill_gold = bill_pred = False
        for gold_line, got in zip(row["lines"], by_name):
            gold, pred = bool(gold_line["anomalous"]), bool(got.is_deviation)
            line_pairs.append((gold, pred))
            bill_gold |= gold
            bill_pred |= pred
            outcome = ("tp" if gold and pred else "fp" if pred else "fn" if gold else "tn")
            per_category[row["category"]][outcome] += 1
            if outcome == "fn":
                if got.status == "not_benchmarked":
                    fn_abstained += 1
                else:
                    fn_fair += 1
            if outcome in ("fp", "fn"):
                failures.append(
                    {"id": row["id"], "line": gold_line["name"], "charged": gold_line["charged"], "outcome": outcome,
                     "status": got.status, "benchmark": got.cghs_benchmark, "note": gold_line.get("note", "")}
                )
        bill_pairs.append((bill_gold, bill_pred))
    lc, bc = binary_counts(line_pairs), binary_counts(bill_pairs)
    logger.info("Anomaly evaluated %d bills / %d lines: %s", len(rows), len(line_pairs), lc)
    return {
        "metric": "billing_anomaly",
        "bills": len(rows),
        "lines": len(line_pairs),
        "line_level": {**lc, **precision_recall_f1(lc["tp"], lc["fp"], lc["fn"]),
                       "accuracy": accuracy(lc["tp"] + lc["tn"], len(line_pairs))},
        "bill_level": {**bc, **precision_recall_f1(bc["tp"], bc["fp"], bc["fn"]),
                       "accuracy": accuracy(bc["tp"] + bc["tn"], len(bill_pairs))},
        "false_negatives_abstained": fn_abstained,
        "false_negatives_judged_fair": fn_fair,
        "per_category": {c: dict(v) for c, v in per_category.items()},
        "failures": failures,
    }
