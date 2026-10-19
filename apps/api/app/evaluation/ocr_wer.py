"""
OCR WER / CER utility.

Scores OCR hypotheses against reference transcriptions. Two uses:

1. ``evaluate_ocr(rows)`` on the bundled fixture (``data/evaluation/ocr_wer_synthetic.jsonl``).
   Its hypotheses are HAND-WRITTEN simulated OCR errors, not the output of any OCR engine,
   so the numbers validate this utility and show how WER/CER react to typical error types;
   they say nothing about Kadi's real OCR accuracy.
2. ``evaluate_ocr(rows, hypotheses=...)`` to score real OCR output (a mapping id -> text)
   against the fixture's references. No OCR engine is run or required by this module.
"""

import logging
from typing import Any, Dict, List, Mapping, Optional

from app.evaluation.metrics import cer, corpus_error_rate, wer

logger = logging.getLogger("arogyarakshak.evaluation.ocr")


def evaluate_ocr(rows: List[Dict[str, Any]], hypotheses: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    per_row = []
    pairs = []
    per_kind: Dict[str, List] = {}
    for row in rows:
        hyp = row["hypothesis"] if hypotheses is None else hypotheses.get(row["id"])
        if hyp is None:
            continue
        pairs.append((row["reference"], hyp))
        per_kind.setdefault(row["error_kind"], []).append((row["reference"], hyp))
        per_row.append({"id": row["id"], "error_kind": row["error_kind"], "wer": wer(row["reference"], hyp),
                        "cer": cer(row["reference"], hyp)})
    logger.info("OCR WER/CER over %d of %d fixture rows", len(pairs), len(rows))
    return {
        "metric": "OCR_WER_CER",
        "rows_scored": len(pairs),
        "rows_total": len(rows),
        "corpus_wer": corpus_error_rate(pairs, "word"),
        "corpus_cer": corpus_error_rate(pairs, "char"),
        "per_error_kind": {
            k: {"rows": len(v), "wer": corpus_error_rate(v, "word"), "cer": corpus_error_rate(v, "char")}
            for k, v in sorted(per_kind.items())
        },
        "per_row": per_row,
    }
