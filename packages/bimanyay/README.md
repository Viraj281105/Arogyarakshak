# BimaNyay (बीमा न्याय — "Insurance Justice")

`packages/bimanyay` is the **insurance claim denial audit, IRDAI appeals, and grievance SLA tracking module** for ArogyaRakshak.

---

## Capabilities & Architecture

BimaNyay empowers policyholders facing unfair health insurance claim rejections or arbitrary deductions:
- **Repudiation Clause Auditor (`bimanyay/clause_auditor.py`)**:
  - Validates rejection reasons against statutory protections in the **IRDAI Master Circular (May 29, 2024)**.
  - Enforces the **5-Year Moratorium Rule** (claims cannot be rejected for pre-existing disease non-disclosure after 5 continuous policy renewal years).
  - Flags improper room rent proportionate deductions applied to ICU or medications.
- **Regulatory Advisor (`bimanyay/regulatory_advisor.py`)**:
  - Gathers formal circular clauses, Section 45 Insurance Act citations, and Insurance Ombudsman Rules 2017.
- **3-Tier Appeal Drafter (`bimanyay/drafter.py`)**:
  - Tier 1: Insurer Grievance Redressal Officer (GRO) representation.
  - Tier 2: Pre-formatted 2,000-character description for the IRDAI Bima Bharosa online portal.
  - Tier 3: Insurance Ombudsman Form VI (Rule 14(1)(b)) petition package.
- **Grievance SLA Tracker (`bimanyay/tracker.py`)**:
  - Manages statutory timelines: Day 3 acknowledgment, Day 15 GRO deadline, Day 30 Bima Bharosa window, 1-year Ombudsman limitation period.

---

## Directory Structure
```text
packages/bimanyay/
├── bimanyay/
│   ├── clause_auditor.py    # Repudiation clause verification vs IRDAI circulars
│   ├── regulatory_advisor.py# Statutory circular and legal citations
│   ├── drafter.py           # 3-tier appeal generator (GRO, Bima Bharosa, Ombudsman)
│   ├── tracker.py           # Statutory SLA calculation and milestone management
│   ├── models.py            # Pydantic schemas
│   └── __init__.py
├── tests/
│   └── test_bimanyay.py     # Unit test suite
├── pyproject.toml
└── README.md
```

---

## Installation & Testing

```bash
# Install as editable package
pip install -e .

# Run unit tests
python -m pytest tests/
```
