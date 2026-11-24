# Kadi (कड़ी — "Link")

`packages/kadi` is the **shared intelligence and context infrastructure** for ArogyaRakshak. It is not an isolated module, but the connective layer upon which all domain modules (`billnyay`, `daavisetu`, `bimanyay`, `schemesetu`, `dawacheck`) depend.

---

## Capabilities & Architecture

- **Document Extraction (`kadi/extraction.py`)**:
  - Ingests raw document text or OCR tokens.
  - Normalizes hospital details, diagnoses, procedures, line items, and medications into a structured schema.
  - The patient name is extracted in memory for the active request only and is never persisted (see `privacy/redaction.py` and ADR-003).
- **Shared OCR Engine (`kadi/ocr/ocr_parser.py`)**:
  - Handles multi-format document parsing (bills, prescriptions, insurance schedules).
  - Devanagari and Latin script text extraction.
  - Returns `ocr_segments` with EasyOCR's per-segment confidence (images only) so uncertain readings can go to human transcription (ADR-011).
- **Clinical review layer (`kadi/clinical_review/`, ADR-011)**: DB-agnostic rules for human clinical review — provenance classes, reviewer verification labels (never "verified" without a real registry check), statement lifecycle and confirmation, frozen evidence packets, safety-rule validation and evaluation, blind two-reader OCR transcription consensus, and the verbatim appeal annex. Persistence lives in `apps/api/app/clinical/`. See `docs/architecture/clinical-review.md`.
- **Vector Store & Indexing**: FAISS similarity indexes for entity blocking. *(planned — not implemented; the unwired scaffold was removed 2026-10-19)*
- **Entity Resolution (`kadi/resolution/`, ADR-006)**:
  - Surface string similarity: Levenshtein, fuzzy token overlap, and conflict guards for strength, dosage form, laterality, variant letters and opposite prefixes (#28)
  - Cross-script phonetic matching: rule-based Devanagari romanization + Indic phonetic keys (#89). **IndicXlit** (`ai4bharat-transliteration`) is not used — fairseq has no Python 3.11 wheels (#29)
  - Cross-lingual semantic similarity via **IndicSBERT** (`l3cube-pune/indic-sentence-similarity-sbert`) — optional `kadi[semantic]` extra, off unless `KADI_SEMANTIC_MATCHING=true` (#30)
  - Merge / ask-user / new-entity branching (#31) and feedback-calibrated thresholds, not RLHF (#88)
  - Evaluation: `kadi/resolution/evaluation.py` and `scripts/evaluate_entity_resolution.py` over a hand-curated synthetic pair set
- **Case graph (`kadi/graph.py`, #86)**: typed node-link projection of a case's entities with per-edge evidence; no graph database.
- **ABDM FHIR import (`kadi/fhir_import.py`, #54)**: client-supplied FHIR R4 bundle -> entity mentions; drops Patient/Practitioner resources. No live gateway pull.
- **Auto-trigger readiness (`kadi/triggers.py`, #32)**: which module checks a case has enough context for.

---

## Directory Structure
```text
packages/kadi/
├── kadi/
│   ├── extraction.py        # Extraction engine (LLM-grounded + heuristic normalization)
│   ├── privacy/             # Dependency-free leaf package (ADR-027): imports nothing else from kadi
│   │   └── redaction.py     # Direct-identifier removal before persistence
│   ├── redaction.py         # Compatibility alias: `from kadi.redaction import redact_pii` still works
│   ├── llm/                 # Resilient Groq client, cache, breaker, shadow runs (ADR-024); imports only kadi.llm and kadi.privacy
│   ├── line_items.py        # Shared billing line-item parsing
│   ├── resolution/          # Entity resolution: similarity, transliteration, phonetic, semantic, resolver, calibration, evaluation
│   ├── graph.py             # Case knowledge-graph projection (#86)
│   ├── fhir_import.py       # ABDM/FHIR bundle -> entity mentions (#54)
│   ├── triggers.py          # Auto-trigger readiness rules (#32)
│   ├── ocr/
│   │   ├── ocr_parser.py    # Optical character recognition parser
│   │   └── tests/           # OCR parser test suite
│   └── __init__.py          # Public package exports (`parse_document` is re-exported lazily, ADR-027)
├── pyproject.toml           # Package configuration & build specification
└── README.md
```

---

## Prompt-injection hygiene (`kadi/injection.py`, #94)
Document text is untrusted. `sanitise_for_prompt` removes invisible and reordering characters
(zero-width space, BOM, soft hyphen, bidi controls, Unicode tag characters, C0 controls) before
text reaches a model; ZWJ/ZWNJ are kept only between two Devanagari characters, where they
change how conjuncts render. `detect_injection_markers` scans a normalised view of the text
(NFKC, hidden characters removed, nukta/chandrabindu and Devanagari digits folded) with English,
Hindi, Marathi and romanised-Hindi phrase patterns. Used by `kadi.extraction` and by BillNyay's
`wrap_untrusted`; a hit is disclosed (`extraction_warnings`, or a log line carrying a count, never
the text) and never silently changes extraction. **Heuristics, not a guarantee:** reworded or
translated attacks and homoglyph substitution are not caught, and the Hindi/Marathi phrase
lists are engineering-team written and **not yet reviewed by a native speaker** (#37).

## Installation & Testing

```bash
# Install as editable package
pip install -e .

# Run Kadi unit tests
python -m pytest
```

For the complete architectural design, see the [Architecture Overview](../../docs/architecture/overview.md).
