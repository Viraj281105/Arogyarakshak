# ADR-006: Kadi Entity Resolution — Signals, Branching, Calibration and Optional IndicSBERT

## Status
Accepted (2026-09-13). Implements #28, #30, #31, #88 and #89. Records why #29 (IndicXlit) is not adopted.

## Context
Until Phase 3, Kadi had no entity resolution. The upload pipeline de-duplicated by exact name within a single upload only, so:

- the same hospital, diagnosis or medicine seen in two documents became two entities;
- re-uploading a document duplicated every entity and added its total to `total_charged` again.

Technical Documentation §4.3 specifies scoring a new mention against the case with three signals: string, transliteration (IndicXlit) and cross-lingual semantics (IndicSBERT). The result branches into merge, ask-user or new entity.

Constraints:

- Python 3.11 and CPU-only torch (`apps/api/constraints-cpu.txt`, issue #141).
- BYOD zero-retention (ADR-003).
- Tests run on SQLite without network access.
- No labelled real-world entity-pair dataset exists.

## Decision

1. **Resolution is pure and lives in `packages/kadi/kadi/resolution/`.** Persistence lives in `apps/api/app/kadi_resolution.py`.
   - Candidates are *blocked* by case and entity type.
   - `billing_item` and `document_text` are never resolved: identical bill lines are separate charges and possible evidence of double billing.
2. **Signals**
   - *Lexical* (#28): normalized Levenshtein, fuzzy core-token Jaccard and containment. Numbers, units, dosage forms and stopwords are excluded from the core tokens.
   - *Phonetic / cross-script* (#89): deterministic Devanagari romanization plus an Indic phonetic key. This handles aspirates, sh/s, ph/f, v/w, soft c/g, vowel length and schwa deletion. For cross-script pairs, the lexical signal compares the romanizations.
   - *Semantic* (#30): IndicSBERT (`l3cube-pune/indic-sentence-similarity-sbert`) through `sentence-transformers`. It is optional and reports `UNAVAILABLE` when off; it is never silently replaced by another embedding.
3. **Combination:** a weighted noisy-OR, `1 − Π(1 − wᵢ·sᵢ)`, with lexical 0.9, phonetic 0.7 and semantic 0.5. Default thresholds are merge ≥ 0.90 and ask ≥ 0.70. **These are uncalibrated defaults chosen by reasoning, not fitted to data.**
4. **Deterministic guards override the score:**
   - Conflicting strength, dosage form, variant letter, laterality or opposite clinical prefix (hyper-/hypo-) makes the mention NEW.
   - Semantic similarity can raise a pair to ASK but never into MERGE. The lexical + phonetic confidence alone must reach the merge threshold. This rule was added after the first real IndicSBERT evaluation merged the look-alike drugs Prednisone / Prednisolone.
   - More than one candidate above the merge threshold is asked.
5. **Persistence**
   - MERGE appends the mention to `meta.mentions` and records an `auto_merged` decision the user can dispute and split.
   - ASK keeps both entities and records a `pending` decision.
   - Identical documents are detected by SHA-256 digest (`kadi_case_documents`); only the digest is stored, never the file.
6. **Feedback calibration (#88):** each confirm/reject becomes a label. Thresholds are recalibrated deterministically:
   - merge threshold set by a precision target, ask threshold by a recall target;
   - at least 30 labels, including at least 8 of each class, are required; otherwise the result is `INSUFFICIENT_EVIDENCE`;
   - each step moves at most ±0.05, clamped to [0.5, 0.99].

   Snapshots are stored in `kadi_threshold_calibrations`. **This is not RLHF**: there is no reward model and no policy optimization.
7. **IndicXlit is not adopted (#29 stays open).** `ai4bharat-transliteration` depends on fairseq, whose latest release (0.12.2) publishes wheels only for CPython 3.6–3.8. The project runs on 3.11. The rule-based romanizer is deliberately not called IndicXlit.
8. **IndicSBERT is an optional extra: `kadi[semantic]`, which means `sentence-transformers>=4.1,<5`.**
   - It is disabled unless `KADI_SEMANTIC_MATCHING=true`.
   - The model (~950 MB, CC-BY-4.0) downloads from the Hugging Face Hub on first use. This is a network endpoint outside Groq, Postgres and the package registries, flagged here per AGENTS.md. Compose keeps it in an `hf_cache` volume.
   - The model ships only `pytorch_model.bin`. transformers refuses `torch.load` on torch < 2.6 because of CVE-2025-32434, so the CPU pins moved from torch 2.4.1 / torchvision 0.19.1 to **2.7.1 / 0.22.1**.

## Consequences

### Positive
- Cross-document and cross-script duplicates merge with provenance; uncertain pairs are asked rather than guessed.
- Duplicate uploads no longer inflate case totals.
- Every decision is explainable: per-signal scores, conflicts and reasons are stored and returned.
- The evaluation harness (`kadi.resolution.evaluation`, `scripts/evaluate_entity_resolution.py`) measures the system against a baseline.

### Negative / limitations
- Weights and default thresholds are heuristic until real feedback accumulates. Calibration labels are selection-biased: only asked or disputed pairs are labelled.
- The evaluation set is hand-curated and synthetic, and was used during development. See `docs/evaluation/entity-resolution.md`.
- Rule-based romanization is lossy (retroflex vs dental, nasals, schwa heuristics).
- Enabling IndicSBERT adds a large download, memory use and CPU latency.
- `create_all` does not alter existing tables, so all persistence was added as new tables.
