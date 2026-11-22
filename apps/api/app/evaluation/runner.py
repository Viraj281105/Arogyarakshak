"""Wires each harness to the PRODUCTION code path and the SYNTHETIC datasets.

Offline and deterministic: nothing here calls Groq or the network (PEA scores the
heuristic fallback extractor, not the LLM path).
"""

import logging
from typing import Any, Dict, Optional

from app.evaluation.anomaly import evaluate_anomaly
from app.evaluation.appeal_completeness import evaluate_appeal_completeness
from app.evaluation.context_reuse import evaluate_context_reuse
from app.evaluation.bma import evaluate_bma
from app.evaluation.crma import evaluate_crma
from app.evaluation.datasets import DATA_DIR, load_dataset
from app.evaluation.dawacheck_mapping import evaluate_dawacheck_mapping
from app.evaluation.grounding import evaluate_grounding
from app.evaluation.ocr_wer import evaluate_ocr
from app.evaluation.pea import evaluate_pea
from app.evaluation.retrieval import evaluate_retrieval_dataset

logger = logging.getLogger("arogyarakshak.evaluation.runner")

DATASETS = {
    "bma": "bma_synthetic.jsonl",
    "pea": "pea_synthetic.jsonl",
    "anomaly": "billing_anomaly_synthetic.jsonl",
    "crma": "crma_synthetic.jsonl",
    "ocr": "ocr_wer_synthetic.jsonl",
    "dawacheck": "dawacheck_mapping_synthetic.jsonl",
    # appeal reuses the CRMA scenario inputs (no new labels: its checks are against each draft's own facts)
    "appeal": "crma_synthetic.jsonl",
    "grounding": "letter_grounding_synthetic.jsonl",
    # Wave 2: tuning set of the retrieval harness (the held-out slice is reported by retrieval_results.json)
    "retrieval": "retrieval_queries_synthetic.jsonl",
    "context_reuse": "context_reuse_synthetic.jsonl",
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


def _bimanyay_documents(payload: Dict[str, Any], language: str):
    """Runs BimaNyay's real drafting path and returns (result, the facts the drafts came from)."""
    from bimanyay import ClaimDenialInput, analyze_insurance_denial

    data = ClaimDenialInput(**payload)
    result = analyze_insurance_denial(data, language=language)
    facts = {
        "policy_number": data.policy_number,
        "insurer_name": data.insurer_name,
        "diagnosis": data.diagnosis,
        "claimed_amount": data.claimed_amount,
        "denied_amount": data.denied_or_deducted_amount,
        "denial_reason": data.denial_reason_raw,
        "grounds": result.primary_dispute_grounds,
        "violations": [v.model_dump() for v in result.regulatory_violations],
    }
    return result, facts


def _appeal(rows):
    def drafter(payload: Dict[str, Any], language: str):
        result, facts = _bimanyay_documents(payload, language)
        return result.level_1_gro_appeal, facts

    return evaluate_appeal_completeness(rows, drafter)


def _grounding(rows):
    _meta, scenarios = load_dataset(DATA_DIR / DATASETS["appeal"])

    def generator(payload: Dict[str, Any], language: str):
        result, facts = _bimanyay_documents(payload, language)
        return [
            ("gro_appeal", result.level_1_gro_appeal, facts),
            ("bimabharosa_summary", result.level_2_bimabharosa_text, facts),
            ("ombudsman_statement", result.level_3_ombudsman_grounds, facts),
        ]

    return evaluate_grounding(rows, scenarios, generator)


def _retrieval(rows):
    _meta, corpus = load_dataset(DATA_DIR / "retrieval_corpus_synthetic.jsonl")
    return evaluate_retrieval_dataset(corpus, rows)


_RUNNERS = {"bma": _bma, "pea": _pea, "anomaly": _anomaly, "crma": _crma, "ocr": _ocr,
            "dawacheck": _dawacheck, "appeal": _appeal, "grounding": _grounding,
            "retrieval": _retrieval, "context_reuse": evaluate_context_reuse}


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
