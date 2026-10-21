"""
Phase-4 evaluation harnesses (BMA, PEA, billing-anomaly P/R/F1, CRMA, OCR WER/CER,
DawaCheck price-mapping accuracy).

Every dataset under ``data/evaluation`` is SYNTHETIC and hand-written; the harnesses
measure behaviour on those known cases, never real-world accuracy. They run offline and
deterministically (no Groq key, no network). Run them with ``scripts/evaluate_phase4.py``.
"""
