# BillNyay (बिल न्याय — "Bill Justice")

`packages/billnyay` is the **hospital bill auditing and overcharging dispute module** for ArogyaRakshak.

---

## Capabilities & Architecture

BillNyay audits itemized hospital bills against government-mandated **Central Government Health Scheme (CGHS)** price schedules and clinical necessity standards using a specialized 5-agent pipeline:

1. **Document Auditor (`billnyay/agents/auditor.py`)**:
   - Parses line items, classifies charges into room rent, ICU, procedures, consultations, and consumables.
   - Benchmarks charged rates against CGHS tier-1/tier-2 rate schedules.
2. **Clinical Reviewer (`billnyay/agents/clinician.py`)**:
   - Validates procedural necessity and flags duplicate or medically incompatible line items.
3. **Regulatory Advisor (`billnyay/agents/regulatory.py`)**:
   - Matches inflated charges with government ceiling guidelines and hospital billing compliance circulars.
4. **Appeal Drafter / Barrister (`billnyay/agents/barrister.py`)**:
   - Drafts a formal, evidence-backed overcharge representation letter addressed to hospital management.
5. **QA Judge (`billnyay/agents/judge.py`)**:
   - Evaluates factual correctness, removes hallucinations, and scores draft completeness before PDF generation.

---

## Directory Structure
```text
packages/billnyay/
├── billnyay/
│   ├── agents/
│   │   ├── auditor.py       # Line-item audit vs CGHS rates
│   │   ├── clinician.py     # Medical necessity validation
│   │   ├── regulatory.py    # Regulatory compliance evaluation
│   │   ├── barrister.py     # Dispute representation letter drafter
│   │   └── judge.py         # QA consensus judge
│   ├── data/                # CGHS rate schedules and reference tables
│   ├── tools/               # Procedural code lookup and math helpers
│   └── __init__.py
├── tests/
│   └── test_agents.py       # Multi-agent unit tests
├── pyproject.toml
└── README.md
```

---

## Installation & Testing

```bash
# Install as editable package
pip install -e .

# Run BillNyay unit tests
python -m pytest tests/
```
