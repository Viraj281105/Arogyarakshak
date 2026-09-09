# DaaviSetu (दावे सेतु — "Claims Bridge")

`packages/daavisetu` is the **pre-claim application and cashless pre-authorization form automation module** for ArogyaRakshak.

---

## Capabilities & Architecture

DaaviSetu bridges the gap between patient hospital records and private insurer paperwork:
- **Pre-Authorization Form Generation (`daavisetu/generator.py`)**:
  - Ingests patient context, estimated procedural costs, hospital details, and treating doctor diagnosis from **Kadi**.
  - Maps fields directly into standardized insurer cashless pre-authorization request schemas.
- **Reimbursement Claim Packaging**:
  - Assembles itemized bill summaries, diagnostic reports, and patient identification into a submission-ready PDF package for manual upload to insurer portals.
- **Explicit Boundary**:
  - DaaviSetu governs the **pre-claim submission** phase. If an insurer repudiates or deducts from the claim, the dispute is handed off to **BimaNyay**.

---

## Directory Structure
```text
packages/daavisetu/
├── daavisetu/
│   ├── generator.py         # Claim form field pre-population engine
│   └── __init__.py
├── tests/
│   └── test_daavisetu.py    # Generator unit tests
├── pyproject.toml
└── README.md
```

---

## Installation & Testing

```bash
# Install as editable package
pip install -e .

# Run DaaviSetu unit tests
python -m pytest tests/
```
