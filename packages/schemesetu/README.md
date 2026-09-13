# SchemeSetu (योजना सेतु — "Scheme Bridge")

`packages/schemesetu` is ArogyaRakshak's **government healthcare scheme eligibility estimator** for:
- **PMJAY** (Ayushman Bharat — Pradhan Mantri Jan Arogya Yojana, national)
- **MJPJAY** (Mahatma Jyotirao Phule Jan Arogya Yojana, Maharashtra state)

Every result is **provisional**. SchemeSetu is deterministic rule matching over a small set of inputs; it is not an official eligibility decision.

---

SchemeSetu matches patients with public healthcare safety nets:
- **Eligibility Rules Engine (`schemesetu/agent.py`)**:
  - Takes annual income, state, social category and medical need, and reports a provisional determination per scheme with claim or verification steps and the official `sources` behind it.
  - Criteria live in `schemesetu/thresholds.py`, the single source of truth. Each scheme carries citations (URL, document, publisher, date, retrieval date) and a `provenance` value:
    - **PMJAY** (`OFFICIAL_SOURCE_CITED`; PIB releases 2116209 of 28 Mar 2025 and 2053883 of 11 Sep 2024): SECC-2011 deprivation/occupational listing or a state-verified database, ASHA/AWW/AWH families, or age 70+ irrespective of income. None of these is collected, so the verdict is always `ambiguous`.
    - **MJPJAY** (`OFFICIAL_RESTATEMENT_CITED`; Government of Maharashtra district portals restating the GR dated 28 July 2023): all families in Maharashtra, so stated residence decides. The GR text and the SHAS portal (jeevandayee.gov.in) were not retrieved, so documentary requirements are unverified.
  - **Income is non-determinative.** Neither scheme defines an annual income ceiling in the cited sources. The earlier ₹2.5L (PMJAY) / ₹1.5L (MJPJAY) limits were unverified project heuristics and were removed; ₹1.5L was MJPJAY's 2020–2024 cover amount, not an income limit.
- **Reasoning, trend and transition helpers** (`reasoning_agent.py` #21, `trend_estimator.py` #70, `transition_adviser.py` #71) and the consent-bounded recommendation trigger (`triggers.py`, #92) read the same criteria. The trigger fires when a scheme newly applies (first saved profile, or a move into Maharashtra); an income change alone never fires, and a projected income cannot change a verdict.

### Not implemented
- **No embeddings, vector index or RAG.** SchemeSetu computes no embeddings. Domain modules may not implement their own embedding layer (`docs/architecture/repository-structure.md`, Kadi Exclusivity); cross-lingual embeddings belong to Kadi's optional IndicSBERT signal (`packages/kadi/kadi/resolution/semantic.py`, ADR-006). The former unwired `embeddings.py` scaffold was removed.
- **No empanelled-hospital directory.** Claim-guide steps advise visiting an empanelled hospital's Ayushman/Arogya Mitra desk, but SchemeSetu holds no hospital data.

---

## Directory Structure
```text
packages/schemesetu/
├── schemesetu/
│   ├── agent.py               # Deterministic eligibility rules (income non-determinative)
│   ├── thresholds.py          # Scheme criteria with official citations (single source of truth)
│   ├── reasoning_agent.py     # Step-by-step trace over the same criteria (#21)
│   ├── triggers.py            # Consent-bounded recommendation trigger (#92)
│   ├── trend_estimator.py     # Income trend projection (#70)
│   ├── transition_adviser.py  # PMJAY <-> MJPJAY transition checklist (#71)
│   └── __init__.py
├── tests/
│   ├── test_schemesetu.py
│   ├── test_income_triggers.py
│   ├── test_reasoning_agent.py
│   ├── test_trend_estimator.py
│   └── test_transition_adviser.py
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
