# Wave 2 - Stream F handoff: matcher fixes

**Branch:** `wave2/f-matchers` (from `wave2/integration` @ 4d34190). Full before/after: `docs/evaluation/matcher-fixes.md`.

## What shipped
1. **BillNyay** `packages/billnyay/billnyay/matching.py` (+ `data/matcher_synonyms.json`): whole-word CGHS key matching, modifier refusal
   (catheter, report, copy, follow-up, drops, guided, contrast agent), small synonym table. `_match_cghs_key` delegates to it and
   `_billing_unit_of` now uses the same match (it had its own substring copy).
2. **Kadi** `line_items.py`: `Name - 400`, trailing payment text, `Total - N` as a summary line.
3. **DawaCheck** `reference_data.py` / `checker.py`: combination products map to a multi-ingredient entry or return None; phonetic path needs
   every drug word covered; phonetic match applies the dosage rule to a bare strength ("Dolo 500").

## Harness results (synthetic; none dropped)
BMA 0.705 -> 0.885; PEA procedure F1 0.942 -> 1.000; anomaly line F1 0.810 -> 0.930; DawaCheck 0.865 -> 0.923.
**Integrator: regenerate the evaluation baseline** (improvements only; the gate has tolerance 0.0 for drops).

## Review-needed / decisions
- `matcher_synonyms.json` is engineering-written, `clinically_reviewed: false`; clinical lead must review it and the modifier list.
- No new `match_method` value was added (the field description is part of the OpenAPI contract and the generated clients); a combination
  resolved through the phonetic path reports `fuzzy_phonetic`.
- `Lap Appendicectomy` now stays unmapped (was a wrong `ppe` rate); no "lap" synonym was added.
- No existing test encoded the old bugs; none was changed.

## Not verified
Real bills, real NPPA/CGHS schedules, independent gold labels; phonetic match with no stated strength still uses the reference ceiling (unchanged).
