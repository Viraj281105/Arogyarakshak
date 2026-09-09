# DawaCheck (दवा चेक — "Medicine Check")

`packages/dawacheck` is the **medicine price benchmarking and generic alternative finder** for ArogyaRakshak.

---

## Capabilities & Architecture

DawaCheck protects consumers from pharmaceutical overcharging and promotes affordable generic medication:
- **NPPA Schedule-I Price Auditing (`dawacheck/checker.py`)**:
  - Benchmarks the Maximum Retail Price (MRP) printed on drug packaging against ceiling prices established by the **National Pharmaceutical Pricing Authority (NPPA)** under the Drugs (Prices Control) Order (DPCO).
  - Flags any illegal overcharging above government-fixed price caps (~800–900 essential Schedule-I formulations).
- **Brand-to-Generic Formulation Mapping**:
  - Resolves branded commercial formulations to their active pharmaceutical ingredients (API) and standardized dosage strengths.
  - Suggests low-cost bioequivalent generic substitutes available through the **Pradhan Mantri Bhartiya Janaushadhi Pariyojana (PMBJP)** network.

---

## Directory Structure
```text
packages/dawacheck/
├── dawacheck/
│   ├── checker.py           # NPPA price verification & generic suggestion logic
│   └── __init__.py
├── tests/
│   └── test_dawacheck.py    # Price check test suite
├── pyproject.toml
└── README.md
```

---

## Installation & Testing

```bash
# Install as editable package
pip install -e .

# Run DawaCheck unit tests
python -m pytest tests/
```
