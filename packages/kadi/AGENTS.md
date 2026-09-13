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
   - `kadi/vector_store.py` is a scaffold for future FAISS/pgvector indexes. It contains no FAISS today and is imported by no endpoint.

5. **Validation**:
   - Run tests from package root:
     ```bash
     python -m pytest packages/kadi/
     ```
