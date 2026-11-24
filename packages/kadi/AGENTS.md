# Scoped Agent Instructions: Kadi Shared Layer (`packages/kadi/`)

Kadi (कड़ी — "link in a chain") is the shared intelligence and context infrastructure connecting all ArogyaRakshak modules.

## Architectural Guidelines for `packages/kadi/`

1. **Shared Context Infrastructure (Not a Fourth Module)**:
   - Kadi does not contain domain-specific pricing or legal rules (those belong in `billnyay`, `daavisetu`, `bimanyay`, `schemesetu`, `dawacheck`).
   - Kadi's sole responsibility is **extracting, resolving, storing, and sharing** patient case context across modules.

2. **Entity Extraction Schema**:
   - Extraction logic lives in `kadi/extraction.py`.
   - Normalizes any document (hospital bill, prescription, insurance letter) into a unified JSON entity schema:
     - `patient_name`, `age`, `gender`
     - `hospital_name`, `admission_date`, `discharge_date`
     - `diagnoses` (with ICD-10 mapping if present)
     - `procedures`
     - `medicines` (brand name, dosage, frequency)
     - `total_amount`, `line_items`

3. **Entity Resolution Pipeline** (`kadi/resolution/`, ADR-006):
   - Multi-signal similarity scoring:
     - Surface string similarity (Levenshtein / fuzzy token overlap) with conflict guards
     - Phonetic / cross-script matching: rule-based Devanagari romanization + Indic phonetic keys. **IndicXlit** is not used (fairseq has no Python 3.11 wheels, #29) — do not describe the rule-based romanizer as IndicXlit.
     - Cross-lingual semantic similarity: **IndicSBERT** (`l3cube-pune/indic-sentence-similarity-sbert`), optional and off by default (`KADI_SEMANTIC_MATCHING`). It may raise a pair to ASK but must never decide a MERGE (the lexical + phonetic confidence alone must reach the merge threshold).
   - Output branching: `High Confidence -> Merge`, `Medium Confidence -> Ask User`, `Low Confidence -> Create New Entity`; conflicts force a new entity.
   - Keep the package DB-agnostic; persistence lives in `apps/api/app/kadi_resolution.py`.
   - Changes to weights, thresholds or guards must be re-evaluated with `scripts/evaluate_entity_resolution.py` (synthetic fixture: zero false merges is a regression floor).

4. **Vector Store & In-Memory Indices**:
   - FAISS/pgvector indexes are planned, not implemented. The unwired `kadi/vector_store.py` scaffold was removed (2026-10-19); add a new module only together with a real caller.

5. **Internal layering (ADR-027)**:
   - `kadi/privacy/` is a dependency-free leaf (no imports from the rest of `kadi`); `kadi/llm/` may import only `kadi.llm` and `kadi.privacy`. Neither may import a root module such as `kadi.extraction` (enforced by `.importlinter` and `tests/test_package_layering.py`).
   - Inside `kadi/llm`, import redaction from `kadi.privacy.redaction`; `kadi.redaction` is only a compatibility alias for outside callers.
   - `kadi/__init__.py` re-exports `parse_document` **lazily** (PEP 562) because `kadi/ocr` imports root modules; never import `kadi.ocr` at the top of `kadi/__init__.py` (a test fails if you do). The static report still lists that edge as a warning (`docs/architecture/code-analysis/kadi/README.md`).

6. **Validation**:
   - Run tests from package root:
     ```bash
     python -m pytest packages/kadi/
     ```
