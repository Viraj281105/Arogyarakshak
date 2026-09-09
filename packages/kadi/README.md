# Kadi (कड़ी — "Link")

`packages/kadi` is the **shared intelligence and context infrastructure** for ArogyaRakshak. It is not an isolated module, but the connective layer upon which all domain modules (`billnyay`, `daavisetu`, `bimanyay`, `schemesetu`, `dawacheck`) depend.

---

## Capabilities & Architecture

- **Document Extraction (`kadi/extraction.py`)**:
  - Ingests raw document text or OCR tokens.
  - Normalizes patient name, age, gender, hospital details, diagnoses, procedures, line items, and medications into a structured schema.
- **Shared OCR Engine (`kadi/ocr/ocr_parser.py`)**:
  - Handles multi-format document parsing (bills, prescriptions, insurance schedules).
  - Devanagari and Latin script text extraction.
- **Vector Store & Indexing (`kadi/vector_store.py`)**:
  - In-memory FAISS similarity indexes for sub-second entity matching and fast blocking.
- **Entity Resolution (Cross-Script & Semantic)**:
  - Surface string distance (Levenshtein / Token overlap)
  - Phonetic transliteration matching via **IndicXlit** (`ai4bharat-transliteration`)
  - Cross-lingual semantic similarity via **IndicSBERT** (`l3cube-pune/indic-sentence-similarity-sbert`)

---

## Directory Structure
```text
packages/kadi/
├── kadi/
│   ├── extraction.py        # Extraction engine (LLM-grounded + heuristic normalization)
│   ├── vector_store.py      # FAISS vector indexing implementation
│   ├── ocr/
│   │   ├── ocr_parser.py    # Optical character recognition parser
│   │   └── tests/           # OCR parser test suite
│   └── __init__.py          # Public package exports
├── pyproject.toml           # Package configuration & build specification
└── README.md
```

---

## Installation & Testing

```bash
# Install as editable package
pip install -e .

# Run Kadi unit tests
python -m pytest
```

For the complete architectural design, see the [Architecture Overview](../../docs/architecture/overview.md).
