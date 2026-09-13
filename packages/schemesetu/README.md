# SchemeSetu (योजना सेतु — "Scheme Bridge")

`packages/schemesetu` is ArogyaRakshak's **government healthcare scheme eligibility estimator** for:
- **PMJAY** (Ayushman Bharat — Pradhan Mantri Jan Arogya Yojana, national)
- **MJPJAY** (Mahatma Jyotirao Phule Jan Arogya Yojana, Maharashtra state)

Every result is **provisional**. SchemeSetu is deterministic rule matching over a small set of inputs; it is not an official eligibility decision.

---

## Capabilities & Architecture

- **Eligibility rules (`schemesetu/agent.py`)**: `check_eligibility(EligibilityRequest)` evaluates two criteria only — annual family income against the scheme income limits, and state of residence (MJPJAY applies only in Maharashtra). `category` and `medical_need` are accepted but do **not** change the verdict. Each `SchemeResult` lists `criteria_evaluated` and `criteria_not_evaluated` (the latter includes SECC-2011 deprivation status and ration-card type) and sets `is_provisional=True`. `confidence_score` is a fixed per-branch heuristic, not a calibrated probability.
- **Income thresholds (`schemesetu/thresholds.py`)**: single source of truth for the limits (PMJAY ₹2,50,000; MJPJAY ₹1,50,000, Maharashtra only). Both carry `provenance="UNVERIFIED_PROJECT_HEURISTIC"` — they have not been verified against official NHA or SHAS Maharashtra guidelines.
- **Reasoning trace (`schemesetu/reasoning_agent.py`)**: `reason_about_eligibility` explains the same determination step by step by walking an explicit Python criteria table. It is not retrieval-augmented generation.
- **Trend estimate (`schemesetu/trend_estimator.py`)**: `project_future_eligibility` fits an ordinary least-squares line to income data points the caller supplies (at least two) and applies the same thresholds to the projected year. No external demographic dataset is used.
- **Transition checklist (`schemesetu/transition_adviser.py`)**: `advise_transition` compares two requests (e.g. before and after relocating, or an income change) and returns generic scheme-transfer housekeeping steps when estimated eligibility changes.
- **Recommendation trigger (`schemesetu/triggers.py`)**: `evaluate_income_trigger` decides from a case's saved income profile (and the previous one) whether a background eligibility run should fire — `FIRE`, `NO_THRESHOLD_CROSSED` or `INSUFFICIENT_EVIDENCE`. The consent check is enforced by the caller in `apps/api`.

### Not implemented
- **No embeddings, vector index or RAG.** SchemeSetu computes no embeddings. Domain modules may not implement their own embedding layer (`docs/architecture/repository-structure.md`, Kadi Exclusivity); cross-lingual embeddings belong to Kadi's optional IndicSBERT signal (`packages/kadi/kadi/resolution/semantic.py`, ADR-006). The former unwired `embeddings.py` scaffold was removed.
- **No empanelled-hospital directory.** Claim-guide steps advise visiting an empanelled hospital's Ayushman/Arogya Mitra desk, but SchemeSetu holds no hospital data.

---

## Directory Structure
```text
packages/schemesetu/
├── schemesetu/
│   ├── __init__.py
│   ├── agent.py               # Income + state rule matching (check_eligibility)
│   ├── thresholds.py          # Income limits and their provenance
│   ├── reasoning_agent.py     # Step-by-step reasoning trace over the same rules
│   ├── trend_estimator.py     # Least-squares projection from caller-supplied income history
│   ├── transition_adviser.py  # PMJAY <-> MJPJAY transition checklist
│   └── triggers.py            # Consent-bounded income-profile recommendation trigger
├── tests/
│   ├── test_schemesetu.py
│   ├── test_reasoning_agent.py
│   ├── test_trend_estimator.py
│   ├── test_transition_adviser.py
│   └── test_income_triggers.py
├── pyproject.toml
└── README.md
```

---

## Installation & Testing

```bash
# Install as editable package
pip install -e .

# Run SchemeSetu unit tests
python -m pytest tests/
```
