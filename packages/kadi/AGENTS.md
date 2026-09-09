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

3. **Entity Resolution Pipeline**:
   - Multi-signal similarity scoring:
     - Surface string similarity (Levenshtein / Token overlap)
     - Phonetic / Cross-script transliteration: **IndicXlit** (`ai4bharat-transliteration`)
     - Cross-lingual semantic similarity: **IndicSBERT** (`l3cube-pune/indic-sentence-similarity-sbert`)
   - Output branching: `High Confidence -> Merge`, `Medium Confidence -> Ask User`, `Low Confidence -> Create New Entity`.

4. **Vector Store & In-Memory Indices**:
   - `kadi/vector_store.py` manages FAISS indexes for lightning-fast blocking and similarity checks.

5. **Validation**:
   - Run tests from package root:
     ```bash
     python -m pytest packages/kadi/
     ```
