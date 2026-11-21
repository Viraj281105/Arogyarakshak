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
  (`packages/bimanyay/tests/golden_en_letters.json`, ten scenarios including the 5.0 / 4.99 year boundary, the `PRE_EXISTING` alias and a lowercase category, every field of the result; regenerate and diff with `golden_en_letters.regen.py` against base commit 4d34190)
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

Source of every number below: the committed outputs of `scripts/terminology_audit.py`,
`docs/evaluation/localised-letters-terminology-before.txt` (package from base commit 4d34190)
and `...-after.txt` (this branch). Sample: a 6-year PED denial with Devanagari user fields, so
any Latin word left in a generated letter is system text; 3 documents x hi, mr, plus BillNyay's
fallback letters and the web/mobile UI copy. The Latin-word rule and allow-list are the audit's
own: `english_allowlist` in `data/terminology/glossary.json`, words of 2+ letters.

| | before | after |
|---|---|---|
| Distinct Latin words outside that allow-list, whole audit | 58 | 7 |
| Occurrences, whole audit | 292 | 22 |

The 7 that remain are not BimaNyay catalogue text: `Tab`, `days`, `ii`, `Paracetamol`,
`Meropenem` are in web/mobile UI copy, `II` and `III` in BillNyay's fallback letter. For the
other four denial categories the audit's sample does not exercise them; the catalogue test
(`test_hi_mr_letters_contain_no_english_sentences`, all ten scenarios, hi and mr, all three
documents) checks that the only Latin tokens left are `IRDAI`, `GRO`, `CRC`, `ICU`, `INR`, the
`UNVERIFIED` marker and the tokens of the circular number `IRDA/HLTH/MISC/CIR`. Those tokens
are **not** in the audit's allow-list (only IRDAI, GRO, CRC, ICU, INR are), so for the delay
category the audit would still list `IRDA`, `HLTH`, `MISC`, `CIR`, and for room rent `UNVERIFIED`.

Harnesses (offline, synthetic, `--check-baseline`): `appeal` mean score 0.8880 (unchanged),
`grounding` hallucination rate 0.0000 and grounding score 1.0000 on 225 letters (unchanged),
`crma` output byte-identical to before. **No regression.**

## 4. Injection detector v2 and the review-round hardening

* `kadi.injection._matching_view` folds a small hand-written table of Cyrillic and Greek
  lookalikes to Latin (before casefolding, so capitals work). Not the full Unicode confusables set.
* Invisible/decorative bypasses are closed in the matching view: variation selectors, the
  combining grapheme joiner, Mongolian FVS, Hangul fillers, the Braille blank, combining marks
  after a non-Devanagari base (`i` + U+0301), precomposed diacritics (`ï`) and the Turkish `İ`
  (NFKC, then NFD, then marks dropped unless they follow a Devanagari base, so matras survive).
  `sanitise_for_prompt` also drops the filler characters (never accents or matras).
* ReDoS: the Hindi/Marathi patterns had unbounded `{_D}*` runs and were quadratic
  (`"नियम" * N`: 1.08 s at 24k characters, 20.5 s at 96k, measured by the reviewer on the
  earlier code). Runs are now bounded (`{0,12}` / `{1,20}`) and the scan is capped at
  `MAX_SCAN_CHARS` = 20,000 characters; hostile 50k-character inputs now run in about 0.02 s
  (timing tests assert < 0.5 s, for the detector and for every pattern on a cap-sized view).
  The text sent to a model is not truncated. **Limitation:** an attack placed after the first
  20,000 characters of a field is not scanned.
* The detector returns pattern **names** (`english-ignore-instructions`, ...), never document
  text. Logs carry counts and names; `extraction_warnings` names the pattern kinds only.

Red-team corpus `data/evaluation/injection_redteam_synthetic.jsonl` (synthetic, hand-written,
UNREVIEWED hi/mr; `_meta` first line): 121 attacks and 102 benign look-alikes (the headline
slice), 6 known-limit rows and a **separate** held-out slice of 30 paraphrase-style attacks
(written by an author who had already seen the patterns, so independence is partial).

| Slice (measured by `test_injection_redteam.py`, `pytest -s`) | v1 | v2 |
|---|---|---|
| Headline attacks flagged | 43/121 | 86/121 |
| Benign look-alikes flagged (false positives) | 5/102 | 5/102 (the same 5, all English) |
| Homoglyph attacks (31) | 0/31 | 31/31 |
| Invisible / combining-mark attacks (12) | 0/12 | 12/12 |
| Paraphrased attacks (outside the patterns, 29) | 0/29 | 0/29 |
| Romanised Hindi (15) | 9/15 | 9/15 |
| **Held-out slice (30), reported separately** | 0/30 | 0/30 |
| Known-limit rows (homoglyphs outside the fold table, 6; expected NOT detected) | 0/6 | 0/6 |

**86/121 is not a detection rate.** It is the author's mix of rows written to be inside the
phrase patterns (`direct`, `translated`: 100% by construction) and rows written to be outside
them (`paraphrase`, held-out: 0%). The meaningful facts are the per-kind lines, the pinned sets
(`injection_redteam_expected.json`: detected is a superset, false positives are exactly the 5
known ids, every hi/mr/Hinglish/other-script benign row is clean) and the gaps: paraphrases,
the whole held-out slice, 6/15 romanised Hindi and any homoglyph outside the table (Armenian,
Cherokee, Cyrillic `г`/`ѓ`) get through. Mutation checks empty the fold table, disable NFD and
empty the filler set and confirm the matching rows then slip through. Real protection stays
architectural (see `kadi.injection`).

## 5. Terminology CI job

`.github/workflows/ci.yml` gains `terminology-audit`: Node 20, `npm ci`, Python 3.11 with the
API requirements and no-deps editable installs, runs `scripts/terminology_audit.py` and uploads
`terminology-report/` (worksheet `.md`, `.json`, summary) as the `terminology-audit-worksheet`
artifact. It is report only: `continue-on-error: true`, `shell: bash` with `set -o pipefail` (a crash is
not hidden by `| tee`), the artifact step runs `if: always()`, and `ci-gate` does not list it in
`needs` (`scripts/tests/ci-workflow.test.mjs` asserts all of this). It is not a translation review.

## 6. Not verified

* Hindi/Marathi wording (all of it) by a native speaker or lawyer.
* The CI job has not run on GitHub; it was checked for YAML validity, the `ci-workflow` Node
  test, and by running the same script locally.
* The Groq-written letter path (not run offline) still produces whatever the model produces.
