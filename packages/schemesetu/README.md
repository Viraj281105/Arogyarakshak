# SchemeSetu (योजना सेतु — "Scheme Bridge")

`packages/schemesetu` is the **government healthcare scheme recommendation and eligibility advisor** for ArogyaRakshak.

---

## Capabilities & Architecture

SchemeSetu matches patients with public healthcare safety nets:
- **Eligibility Reasoning Agent (`schemesetu/agent.py`)**:
  - Ingests patient demographics (ration card category, annual household income, state/district) and medical needs.
  - Matches parameters against statutory guidelines for:
    - **PMJAY** (Ayushman Bharat — Pradhan Mantri Jan Arogya Yojana, national)
    - **MJPJAY** (Mahatma Jyotirao Phule Jan Arogya Yojana, Maharashtra state)
  - Outputs a plain-language eligibility determination and claim walkthrough.
- **Offline Semantic Embeddings (`schemesetu/embeddings.py`)**:
  - Employs an ONNX-runtime SentenceTransformer embedding pipeline for offline, local fallback semantic retrieval over scheme rules.
- **Empanelled Network Hospitals**:
  - Retrieves registered public and private hospitals empanelled under PMJAY and MJPJAY for the patient's district.

---

## Directory Structure
```text
packages/schemesetu/
├── schemesetu/
│   ├── agent.py             # Rule matching and RAG reasoning agent
│   ├── embeddings.py        # ONNX embedding runtime & similarity scoring
│   └── __init__.py
├── tests/
│   └── test_schemesetu.py   # Eligibility evaluation test suite
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
