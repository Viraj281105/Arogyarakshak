# Matcher fixes (Wave 2 / stream F): before and after

Fixes for follow-ups 1, 2 and 4 in `phase4-harnesses.md`. Measured with
`python scripts/evaluate_phase4.py --json ...` on the same **synthetic** datasets and gold labels as before
(no dataset or label was edited). n: BMA 78 lines, PEA 28 bills / 72 items, anomaly 70 lines / 39 bills,
DawaCheck 52 queries. These are small invented sets; the numbers describe behaviour on them, not field accuracy.

## Before / after

| Metric | Before | After |
|---|---|---|
| BMA accuracy | 0.705 (55/78) | 0.885 (69/78) |
| BMA outcomes (correct / wrong_key / missed / false_match) | 55 / 1 / 14 / 8 | 69 / 0 / 9 / 0 |
| BMA mapping precision / recall / F1 | 0.820 / 0.732 / 0.774 | 1.000 / 0.839 / 0.913 |
| PEA procedure F1 (P / R) | 0.942 (0.950 / 0.934) | 1.000 (1.000 / 1.000) |
| PEA all-items F1 | 0.951 | 1.000 |
| Anomaly line P / R / F1 | 0.895 / 0.739 / 0.810 | 1.000 / 0.870 / 0.930 |
| Anomaly bill P / R / F1 | 0.875 / 0.700 / 0.778 | 1.000 / 0.850 / 0.919 |
| DawaCheck accuracy | 0.865 (45/52) | 0.923 (48/52) |
| DawaCheck wrong_drug / false_match / missed | 1 / 2 / 4 | 0 / 0 / 4 |
| DawaCheck per-unit ceiling correct | 0.967 (29/30) | 1.000 (31/31) |

`python scripts/check_eval_regression.py` (tolerance 0.0) after the final change printed `RESULT: PASS (improvements found ...)`: every gated
metric is IMPROVED or OK, none REGRESSED (e.g. `bma.accuracy 0.7051 -> 0.8846 IMPROVED`, `dawacheck.accuracy 0.8654 -> 0.9231 IMPROVED`,
`pea.medicines.f1 1.0 -> 1.0 OK`). Every BMA row that was correct before is still correct (frozen list in
`apps/api/tests/test_matcher_bma_regression.py`).

## What changed

**BillNyay** (`packages/billnyay/billnyay/matching.py`, used by `_match_cghs_key` and now also
`_billing_unit_of`, which previously carried its own substring copy):
- keys match as whole words, hyphens/punctuation are word breaks (`ppe` no longer inside "appendectomy"/"upper",
  `icu` no longer inside "particular"; "X-Ray" == "x ray");
- modifier words that change what is billed (catheter, report, copy, follow-up, drops, guided, and "contrast" not
  preceded by with/without) refuse the match instead of using the parent rate; "CT Scan Abdomen with contrast" still maps;
- small synonym table `data/matcher_synonyms.json` (USG/sonography, xray, PTCA/angioplasty, haemodialysis). **Written by
  engineering, not clinically reviewed** (`clinically_reviewed: false`); needs clinical-lead review.

**Kadi** (`line_items.py`): `Name - 400` (a hyphen/dash with whitespace on both sides) no longer leaves a hyphen in the name;
a payment remark after the amount (`(paid)`, `paid`, `only`, `/-`, `(cash)`...) is tolerated; `Total - N` is a summary line.
Trailing text is accepted only when the amount carries an explicit price marker (colon, dash or currency), so `Pan 40 (Strip of 15)`
and `Dolo 650 paid` are still not read as charges.

**DawaCheck** (`reference_data.py`, `checker.py`): a query naming two or more drugs (a `+ & / and with` marker, or two strengths)
maps only to a multi-ingredient reference entry whose every ingredient is named, else returns None; the phonetic path now requires
every drug word in the query to be covered by the entry; a phonetic match with a bare strength ("Dolo 500") is scaled by the dosage rule.

## Rows that changed

BMA, now correct (was wrong): BMA-064 Appendectomy (Open), 066 Endoscopy Upper GI, 069 Dialysis Catheter Insertion, 070 Particular Care
Charges, 071 Meticulous Dressing Charges, 073 Consultation Report Copy Fee, 074 MRI Contrast Agent, 078 Cataract Surgery Follow-up
Drops (all false_match to a rate); BMA-040 ct-scan chest, 041 X Ray Chest, 042 Xray Knee, 043 USG Abdomen, 044 Sonography Pelvis, 046 Angioplasty (PTCA) (missed -> mapped).
BMA-045 Lap Appendicectomy was a wrong_key (`ppe` rate); it is now unmapped, i.e. `missed` (safe) but NOT correct.
Still missed (safe): 025, 045, 047, 048, 049, 050, 053, 054, 056 (no synonym added: not requested, would need clinical review).

PEA: the 2 awkward bills (hyphen separator, trailing text) now extract exactly (3 fp and 4 fn -> 0).

Anomaly: the 2 false positives (ANOM-037 *Ultrasound Guided Biopsy*, ANOM-038 *Dialysis Catheter Insertion x 1*) are gone; 3 of the 6
abstained false negatives are now benchmarked and flagged (ANOM-033 *Sonography Pelvis*, 034 *CT-Scan Head*, 035 *X Ray Chest*).
Still abstentions: ANOM-031 and 032 (recurring rate, no stated count) and ANOM-036 *Haemodialysis Session*, which now maps to
`dialysis` but is a per-session rate with no stated count, so it is correctly not compared.

DawaCheck: DAWA-033 Dolo 500 (ceiling 2.30 -> 1.77), DAWA-035 Amoxicillin Clavulanate 625 (wrong_drug -> correct combination
entry), DAWA-048 Paracetamol + Ibuprofen and DAWA-049 Pantoprazole + Domperidone (false_match -> refused). Still missed (safe,
brand not in alias list): Azee 500, Pantop 40, Zithromax 500, Amoxyclav 625.

## Review round 1 additions (all pinned by tests)
**BillNyay matcher**
- A key must appear inside the line; a bare fragment ("scan", "ward", "private") maps to nothing (the old either-direction substring match applied a
  rate by dict order). No BMA row depended on it.
- Ambiguity: two unrelated keys with different rate/unit ("ICU Consultation", "MRI and CT Scan") return None; a refinement ("icu day charges" over "icu") is fine.
- Qualifiers refuse: non, excluding, step(-down), paediatric, neonatal. Contrast agent/media/injection/dye is refused even after "with".
- Conservative plural folding (X-Rays, CT Scans, Blood Tests); Devanagari text in a line refuses the match.
- The bare `angioplasty` synonym was removed (could be peripheral/renal/carotid); only PTCA maps to coronary angioplasty. BMA-046 "Angioplasty (PTCA)" still maps.
- Over-refusals kept on purpose (refusing beats a wrong price): "CT Scan Report", "contrast CT scan", "CT Scan - contrast", "Ultrasound Abdomen with report".
- If `matcher_synonyms.json` fails to load, an ERROR is logged (no document text) instead of silently disabling the refusals.

**DawaCheck**
- A combination is never scaled from one component's strength: "Amoxicillin 500mg + Clavulanate 125mg" maps unscaled (components sum to 625);
  other strengths ("Amoxicillin + Clavulanate 375", "Augmentin 375mg") are refused.
- Combinations with no marker or with "plus" ("Amoxicillin 500mg Clavulanate", "Paracetamol 650mg Plus Caffeine") are refused: any drug word an exact/alias hit does not cover refuses it.
- A bare number is a strength only when alone: pack sizes ("15s", "x 15", "strip of 10", "10 tablets", "qty 30") and codes (b12) are ignored.
- INTENDED refusals of lines that might be single-drug: "Crocin Advance 500", "Crocin Advance 500mg / 10 tablets", "Metformin Prolonged Release 500mg"
  (an unaccounted-for word is treated as a different product). "with meals"/"with food", "tablet", "caps", "tabs" are not treated as drugs and still map.

## Not verified / limits
- Gold labels were written by the same team; no independent annotator, no real bills.
- The synonym table and the modifier list are unreviewed clinical content.
- A phonetic match with no stated strength at all still uses the reference strength's ceiling (existing behaviour, not changed).
- A bare number is read as mg only on the phonetic path and only when unambiguous (one number, no pack marker).
