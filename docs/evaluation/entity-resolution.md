# Kadi Entity Resolution — Evaluation

> **Read this first.** Every number below comes from a **hand-curated, synthetic** set of 100
> mention/candidate pairs, written by the team. It was used *while developing* the resolver, so
> it is a development set, not a held-out test set. The numbers describe how the resolver behaves
> on known hard cases. They are **not** a measure of real-world accuracy.

## Dataset
`packages/kadi/tests/fixtures/entity_pairs_curated_synthetic.jsonl` contains 100 pairs: 96 labelled and 4 deliberately ambiguous. The ambiguous pairs (`same_entity: null`) are excluded from precision and recall.

| Category | Pairs | Label | What it probes |
|---|---|---|---|
| spelling_variant | 16 | same | Typos, alternate spellings, abbreviations, salt names |
| qualifier_variant | 8 | same | Strength/unit formatting, word order, punctuation |
| transliteration_hindi | 16 | same | Devanagari (Hindi) ↔ Latin |
| transliteration_marathi | 6 | same | Devanagari (Marathi, incl. ॅ/ॉ/ॲ) ↔ Latin |
| translation | 13 | same | Hindi/Marathi word ↔ English concept (बुखार ↔ Fever) |
| hard_negative_dosage | 11 | different | Strength, dosage form, laterality, variant letter, type 1/2 |
| hard_negative_similar_name | 20 | different | Look-alike/sound-alike drugs, opposite conditions, branches |
| semantic_distractor | 5 | different | Related but different concepts (fever ↔ headache) |
| non_resolvable_type | 1 | different | Identical bill lines (never merged) |
| ambiguous | 4 | null | Brand vs generic, colloquial terms, possible branch |

## Method
Each pair is resolved as one mention against one candidate. MERGE is the positive prediction.

- **Review recall:** the share of true matches that were merged *or* sent to ASK, i.e. not silently created as a separate entity.
- **Silent miss:** a true match decided NEW.
- **Baseline:** classic Soundex on the first word.

Reproduce:

```bash
python scripts/evaluate_entity_resolution.py
python scripts/evaluate_entity_resolution.py --semantic --json eval.json
```

`--semantic` needs `packages/kadi[semantic]`, torch ≥ 2.6 and the IndicSBERT model.

Measured on 2026-09-13 with the Phase-3 code:

- **Environment:** the API Docker image (`python:3.11-slim`, torch 2.7.1+cpu, sentence-transformers 4.1.0, transformers 4.57.6), on CPU only.
- **Model:** `l3cube-pune/indic-sentence-similarity-sbert`.
- **Latency:** per pair on a development laptop.

## Results

| Configuration | Merge precision | Merge recall | Merge F1 | Review recall | False merges | Silent misses | Ask rate | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| lexical only | 1.000 | 0.542 | 0.703 | 0.746 | 0 | 15 | 0.19 | 0.12 | 0.31 |
| lexical + phonetic | 1.000 | 0.729 | 0.843 | 0.780 | 0 | 13 | 0.14 | 0.19 | 0.39 |
| lexical + phonetic + semantic (IndicSBERT) | 1.000 | 0.729 | 0.843 | 0.831 | 0 | 10 | 0.20 | 64.5 | 253.6 |
| baseline: Soundex (first word) | 0.667 | 0.576 | 0.618 | – | 17 | – | – | – | – |

Per category, for lexical + phonetic + semantic (merge / ask / new):

| Category | Merge | Ask | New |
|---|---|---|---|
| spelling_variant (16) | 13 | 3 | 0 |
| qualifier_variant (8) | 8 | 0 | 0 |
| transliteration_hindi (16) | 16 | 0 | 0 |
| transliteration_marathi (6) | 6 | 0 | 0 |
| translation (13) | 0 | 3 | 10 |
| hard_negative_dosage (11) | 0 | 0 | 11 |
| hard_negative_similar_name (20) | 0 | 13 | 7 |
| semantic_distractor (5) | 0 | 0 | 5 |
| non_resolvable_type (1) | 0 | 0 | 1 |
| ambiguous (4) | 0 | 1 | 3 |

## Findings
1. **No false merges** in any configuration on this set. The Soundex baseline makes 17 false matches, mostly different strengths of the same drug and look-alike drug names. The deterministic conflict guards (strength, form, laterality, variant letter, hyper-/hypo-) are what prevent these.
2. **The rule-based cross-script phonetic signal matters most.** It raised merge recall from 0.542 to 0.729, and all 22 Hindi/Marathi transliteration pairs merged. This is not IndicXlit (see ADR-006, #29).
3. **IndicSBERT's contribution is modest here.**
   - It moved 3 of 13 translation pairs to ASK: ER-047 बुखार/Fever, ER-049 मधुमेह/Diabetes, ER-055 दिल का दौरा/Heart attack. The other 10 remain silent misses.
   - It never merges by design, so merge recall is unchanged.
   - It costs about 64 ms p50 / 254 ms p95 per comparison on CPU, against well under 1 ms without it.

   That trade-off is why it stays off by default.
4. **The evaluation found a real defect, which was fixed.** The first IndicSBERT run merged ER-074 **Prednisone / Prednisolone**, two different drugs: embedding similarity lifted a look-alike pair over the merge threshold. The resolver now requires the lexical + phonetic confidence alone to reach the merge threshold, so semantic similarity can only lead to ASK. The table above is after that fix. Because the fix was motivated by this set, the post-fix number is not an unbiased estimate.
5. **About 14–20% of pairs go to the user.** Most are look-alike drugs (Amoxicillin/Ampicillin, Hydroxyzine/Hydralazine) and partial matches (Dengue / Dengue fever). Asking is the intended outcome when names cannot establish identity.

## Limitations
- Synthetic, small (100 pairs), labelled by the developers, and used during development. No confidence intervals are reported, because they would imply sampling from a real population.
- Pair-level only. Blocking with several candidates, OCR noise distributions and real extraction errors are covered by unit/API tests, not measured here.
- Merge weights and thresholds are uncalibrated defaults. Real calibration needs labelled feedback from real use (#88), and those labels are biased towards pairs that reached ASK.
- A real evaluation needs a labelled entity-pair set drawn from consented, de-identified real documents (Phase 4 backlog). Until then, treat these figures as regression floors, not accuracy claims.
