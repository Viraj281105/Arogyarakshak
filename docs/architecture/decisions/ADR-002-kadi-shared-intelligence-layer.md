# ADR-002: Kadi Shared Intelligence & Context Layer

## Status
Accepted

## Context
Early prototypes ran isolated document ingestion and OCR parsers inside each module. When a patient uploaded a hospital bill in BillNyay and later wanted to verify SchemeSetu eligibility, they were forced to re-upload the same document and answer identical questions.

## Problem
Duplicated parsers caused inconsistent schema outputs, wasted inference tokens, and created a fragmented user experience.

## Decision
We established **Kadi (`packages/kadi`)** as shared infrastructure:
1. Kadi is **not** an isolated application module; it is the platform's central data extraction and entity resolution foundation.
2. All document OCR, entity extraction, phonetic transliteration (**IndicXlit**), and cross-lingual semantic matching (**IndicSBERT**) live exclusively in Kadi.
3. Once Kadi extracts context into `kadi_cases`, any authorized module can query the case entities without requesting re-uploads.

## Consequences
### Positive
- Single document upload produces cross-cutting insights (e.g. BillNyay detects overcharging while SchemeSetu alerts the patient to PMJAY eligibility).
- De-duplicated ML pipelines and shared phonetic transliteration tables.
### Negative
- Changes to Kadi's core extraction schema can impact all five domain modules; rigorous regression testing in `packages/kadi/` is mandatory.
