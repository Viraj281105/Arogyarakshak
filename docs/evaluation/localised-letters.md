# Localised appeal letters, injection v2 and the terminology CI job (Wave 2, stream D)

Status: **UNREVIEWED.** Every Hindi and Marathi string described here was written by the
engineering team (a model) and is marked `NEEDS NATIVE-SPEAKER QA` (tracked in #37). Nothing in
this document says the wording is correct, idiomatic or legally precise.

## 1. The finding this fixes

`docs/evaluation/terminology-audit.md` found that Hindi and Marathi appeal letters embedded
English: the template around the grounds was localised, but `audit_claim_denial` returned
English grounds, violation summaries and statute/clause names whatever the letter language.

## 2. What shipped

`packages/bimanyay/bimanyay/catalogue.py` is a structured message catalogue:

| Group | Keys |
|---|---|
| Grounds | `default` (general/other), `ped_moratorium`, `ped_documentary`, `investigation`, `room_rent`, `delay` |
| Violations (statute, clause, summary, remedy) | `moratorium`, `investigation`, `room_rent`, `delay`, `crc` |

each in `en`, `hi`, `mr`, with `str.format` parameters (`{policy_age_years}`, `{diagnosis}`).
`audit_claim_denial(input, language="en")` reads from it; `analyze_insurance_denial` passes the
letter language through. The decision and the reversal prior never depend on the language
(tested). An unknown language falls back to English, like the drafters.

Decisions:

* The English strings are the original text; a golden test
  (`packages/bimanyay/tests/golden_en_letters.json`, six scenarios, every field of the result)
  proves the English output is **byte-identical** to before.
* Acronyms and cited identifiers stay Latin: `IRDAI`, `GRO`, `CRC`, `ICU`, and the circular
  number `IRDA/HLTH/MISC/CIR/216/09/2011`. The marker `UNVERIFIED` also stays Latin in the
  room-rent clause reference because the appeal-completeness harness counts citations whose
  clause reference starts with it (`unverified_clause_citations`); localising it would have
  silently changed that metric for hi/mr.
* Hindi/Marathi grounds avoid the word "डॉक्टर": the grounding harness treats `डॉ…` as a
  clinician-opinion claim that can never be grounded (ADR-011). A test guards this.
* Clause numbers (`खंड 16`, `कलम 16`) are written with ASCII digits and extractable by the
  grounding harness.

## 3. Measured effect

Terminology audit (`scripts/terminology_audit.py`, sample: 6-year PED denial, Devanagari user
fields so any Latin is system text; 3 documents x hi, mr):

| | before | after |
|---|---|---|
| Distinct Latin words outside the allow-list, whole audit | 58 | 7 |
| Occurrences, whole audit | 292 | 22 |
| Of those, words appearing in the BimaNyay letters | 51 distinct | 0 |

The 7 that remain (`II`, `III`, `Meropenem`, `Paracetamol`, `Tab`, `days`, `ii`) are in BillNyay's
fallback letter and UI copy, outside this stream. Across all five categories x hi/mr (30
letters) the Latin words left in the BimaNyay letters are the circular-number tokens
(`IRDA/HLTH/MISC/CIR`, 8 each) and `UNVERIFIED` (2), 34 occurrences in total, down from 1,258
(155 distinct words), measured with the audit's own word rule and allow-list.

Harnesses (offline, synthetic, `--check-baseline`): `appeal` mean score 0.8880 (unchanged),
`grounding` hallucination rate 0.0000 and grounding score 1.0000 on 225 letters (unchanged),
`crma` output byte-identical to before. **No regression.**

## 4. Injection detector v2

`kadi.injection._matching_view` now folds a small hand-written table of Cyrillic and Greek
lookalikes (о, а, е, р, с, і ..., Greek ο, ι, α, ε, capital Nu = N ...) to Latin, before
casefolding so capitals work. The folding is in the matching view only: text sent to a model
is never rewritten. It is not the full Unicode confusables set.

Red-team corpus `data/evaluation/injection_redteam_synthetic.jsonl`: `_meta` first line
(`"synthetic": true`), then 109 attacks and 102 benign look-alikes. Hand-written; homoglyph
rows are produced by deterministic character substitution. Rows of kind `direct`/`translated`
were written to be inside the phrase patterns and `paraphrase` rows outside them, so the
overall rate is a mixed number. Several benign rows are ones the English patterns do match
(`you are now discharged`, `act as a diuretic`, `system prompt payment discount`); they are kept
on purpose.

Measured by `packages/kadi/tests/test_injection_redteam.py` (printed with `pytest -s`):

| | v1 (before) | v2 |
|---|---|---|
| Attacks detected | 43/109 = 0.394 | 74/109 = 0.679 |
| Benign flagged (false positives) | 5/102 = 0.049 | 5/102 = 0.049 |
| Homoglyph attacks (Cyrillic, Greek, in Hindi/Marathi/Hinglish) | 0/31 | 31/31 |
| Paraphrased attacks (outside the patterns) | 0/29 | 0/29 |
| Romanised Hindi (Hinglish) | 9/15 | 9/15 |

The test asserts only floors under what was observed (detection >= 0.60, false positives <=
0.08) and that paraphrase detection stays low; a mutation check empties the confusable table
and confirms homoglyph detection collapses. **This is not immunity**: paraphrases, most
romanised Hindi, and any homoglyph outside the table get through, and the corpus was written
by the same team that wrote the patterns, so the true rate against real attackers is unknown
and likely lower. Real protection stays architectural (see `kadi.injection`).

## 5. Terminology CI job

`.github/workflows/ci.yml` gains `terminology-audit`: Node 20, `npm ci`, Python 3.11 with the
API requirements and no-deps editable installs, runs `scripts/terminology_audit.py` and uploads
`terminology-report/` (worksheet `.md`, `.json`, summary) as the `terminology-audit-worksheet`
artifact. It is report only: `continue-on-error: true`, and `ci-gate` does not list it in
`needs`. It is not a translation review.

## 6. Not verified

* Hindi/Marathi wording (all of it) by a native speaker or lawyer.
* The CI job has not run on GitHub; it was checked for YAML validity, the `ci-workflow` Node
  test, and by running the same script locally.
* The Groq-written letter path (not run offline) still produces whatever the model produces.
