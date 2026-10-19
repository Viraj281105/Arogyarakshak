"""Wires each harness to the PRODUCTION code path and the SYNTHETIC datasets.

Offline and deterministic: nothing here calls Groq or the network (PEA scores the
heuristic fallback extractor, not the LLM path).
"""

import logging
from typing import Any, Dict, Optional

from app.evaluation.anomaly import evaluate_anomaly
from app.evaluation.bma import evaluate_bma
from app.evaluation.crma import evaluate_crma
from app.evaluation.datasets import DATA_DIR, load_dataset
from app.evaluation.dawacheck_mapping import evaluate_dawacheck_mapping
from app.evaluation.ocr_wer import evaluate_ocr
from app.evaluation.pea import evaluate_pea

logger = logging.getLogger("arogyarakshak.evaluation.runner")

DATASETS = {
    "bma": "bma_synthetic.jsonl",
    "pea": "pea_synthetic.jsonl",
    "anomaly": "billing_anomaly_synthetic.jsonl",
    "crma": "crma_synthetic.jsonl",
    "ocr": "ocr_wer_synthetic.jsonl",
    "dawacheck": "dawacheck_mapping_synthetic.jsonl",
}


def _bma(rows):
    from app.services import billnyay_audit as bn

    rates = bn.CGHS_RATES if bn.CGHS_RATES else bn._load_cghs_rates()
    return evaluate_bma(rows, lambda line: bn._match_cghs_key(line, rates))


def _pea(rows):
    from kadi.extraction import run_heuristic_extraction_fallback

    return evaluate_pea(rows, run_heuristic_extraction_fallback)


def _anomaly(rows):
    from app.services.billnyay_audit import audit_billing_lines

    return evaluate_anomaly(rows, audit_billing_lines)


def _crma(rows):
    from bimanyay import ClaimDenialInput, assess_clinical_review_need, audit_claim_denial

    def auditor(payload: Dict[str, Any]) -> Dict[str, Any]:
        data = ClaimDenialInput(**payload)
        wrongful, _prob, _grounds, violations = audit_claim_denial(data)
        clinical = assess_clinical_review_need(data.denial_category, data.denial_reason_raw, data.diagnosis)
        return {
            "is_wrongful": wrongful,
            "citations": [f"{v.statute_or_circular} {v.clause_reference}" for v in violations],
            "clinical": clinical.requires_clinical_interpretation,
        }

    return evaluate_crma(rows, auditor)


def _ocr(rows):
    return evaluate_ocr(rows)


def _dawacheck(rows):
    from dawacheck.checker import benchmark_medicine

    return evaluate_dawacheck_mapping(rows, lambda q: benchmark_medicine(q, 1.0))


_RUNNERS = {"bma": _bma, "pea": _pea, "anomaly": _anomaly, "crma": _crma, "ocr": _ocr, "dawacheck": _dawacheck}


def run_all(only: Optional[str] = None) -> Dict[str, Any]:
    """Runs every harness (or one) and returns {name: {"dataset": meta, **report}}."""
    out: Dict[str, Any] = {}
    for name, filename in DATASETS.items():
        if only and name != only:
            continue
        meta, rows = load_dataset(DATA_DIR / filename)
        report = _RUNNERS[name](rows)
        out[name] = {"dataset": meta, **report}
    return out
