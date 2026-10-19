"""
CRMA — Claim-Rejection Mapping Accuracy.

Does a claim-repudiation scenario map to the right dispute outcome in BimaNyay
(``audit_claim_denial`` + ``assess_clinical_review_need``)? Scored on 25 SYNTHETIC
scenarios (``data/evaluation/crma_synthetic.jsonl``) whose labels are the team's reading of
the IRDAI rules — not legal advice and not lawyer-verified.

Three checks per scenario:

- ``wrongful``   engine's ``is_wrongful`` equals the gold label
- ``clause``     (only when gold names one) a returned violation's statute/clause text
                 contains the expected substring
- ``clinical``   ``requires_clinical_interpretation`` equals the gold label

CRMA = share of scenarios where every applicable check passes. Wrongful-denial P/R/F1 uses
"wrongful" as the positive class.
"""

import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List

from app.evaluation.metrics import accuracy, binary_counts, precision_recall_f1

logger = logging.getLogger("arogyarakshak.evaluation.crma")

Auditor = Callable[[Dict[str, Any]], Dict[str, Any]]
# auditor(input dict) -> {"is_wrongful": bool, "citations": [str], "clinical": bool}


def evaluate_crma(rows: List[Dict[str, Any]], auditor: Auditor) -> Dict[str, Any]:
    wrongful_pairs = []
    clause_total = clause_hit = clinical_ok = full_ok = 0
    per_group: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    failures: List[Dict[str, Any]] = []
    for row in rows:
        got = auditor(row["input"])
        w_ok = got["is_wrongful"] == row["expected_is_wrongful"]
        wrongful_pairs.append((row["expected_is_wrongful"], got["is_wrongful"]))
        clause = row.get("expected_clause")
        c_ok = True
        if clause:
            clause_total += 1
            c_ok = any(clause.lower() in text.lower() for text in got["citations"])
            clause_hit += c_ok
        k_ok = got["clinical"] == row["expected_clinical_review"]
        clinical_ok += k_ok
        ok = w_ok and c_ok and k_ok
        full_ok += ok
        per_group[row["group"]]["n"] += 1
        per_group[row["group"]]["correct"] += ok
        if not ok:
            failures.append(
                {"id": row["id"], "group": row["group"], "category": row["input"]["denial_category"],
                 "wrongful": {"gold": row["expected_is_wrongful"], "got": got["is_wrongful"]},
                 "clause": {"expected": clause, "ok": c_ok} if clause else None,
                 "clinical": {"gold": row["expected_clinical_review"], "got": got["clinical"]}}
            )
    n = len(rows)
    wc = binary_counts(wrongful_pairs)
    logger.info("CRMA evaluated %d scenarios, %d fully correct", n, full_ok)
    return {
        "metric": "CRMA",
        "scenarios": n,
        "crma": accuracy(full_ok, n),
        "wrongful_accuracy": accuracy(wc["tp"] + wc["tn"], n),
        "wrongful": {**wc, **precision_recall_f1(wc["tp"], wc["fp"], wc["fn"])},
        "clause_checks": clause_total,
        "clause_accuracy": accuracy(clause_hit, clause_total),
        "clinical_accuracy": accuracy(clinical_ok, n),
        "per_group": {g: dict(v) for g, v in per_group.items()},
        "failures": failures,
    }
