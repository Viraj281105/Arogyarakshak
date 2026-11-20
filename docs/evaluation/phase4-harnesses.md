# Phase-4 Evaluation Harnesses — BMA, PEA, Billing-Anomaly, CRMA, OCR WER/CER, DawaCheck Mapping, Appeal Completeness, Letter Grounding

> **Read this first.** Every number below comes from **SYNTHETIC, hand-written** datasets in
> `data/evaluation/`. They were written by the team, the labels were assigned *before* the
> first run, and the code under test was then run against them. They show how the current
> code behaves on known cases — **including cases deliberately chosen to be hard**. They are
> **not** real-world accuracy, not a held-out test, and not independently reviewed (the CRMA
> labels are not lawyer-verified). Every dataset file starts with a `_meta` record carrying
> `"synthetic": true`, and the loader (`app/evaluation/datasets.py`) refuses any file that
> does not. The hard-case share is large on purpose, so these figures are *lower* than a
> random sample of ordinary bills would likely give; do not quote them as "the system is X%
> accurate".

All harnesses run offline and deterministically — no Groq key, no network. PEA scores the
**offline heuristic fallback extractor**, not the LLM path (which is not measured anywhere).

## Reproduce

```bash
python scripts/evaluate_phase4.py                    # all eight, summary + every failure
python scripts/evaluate_phase4.py --only bma         # bma|pea|anomaly|crma|ocr|dawacheck|appeal|grounding
python scripts/evaluate_phase4.py --json out.json    # full reports
python -m pytest apps/api/tests/test_evaluation_harness.py apps/api/tests/test_evaluation_appeal_grounding.py
```

Code: `apps/api/app/evaluation/` (`metrics.py` pure metric functions, one module per metric,
`runner.py` wires each to the production code path). Tests use tiny inputs with
hand-computed expected values. Measured on 2026-10-19 on the `main` code at 16e234e plus this PR.

## Summary

| Harness | Dataset (synthetic) | Headline | Measured |
|---|---|---|---|
| **BMA** (bill line → CGHS rate key) | 78 lines | mapping accuracy | **0.705** (55/78); mapping P/R/F1 0.820 / 0.732 / 0.774 |
| **PEA** (bill text → procedure lines) | 28 mock bills, 72 gold line items | procedure P/R/F1 | **0.950 / 0.934 / 0.942** (57 tp, 3 fp, 4 fn) |
| **Billing anomaly** | 39 bills, 70 lines | line-level P/R/F1 | **0.895 / 0.739 / 0.810** (bill-level 0.875 / 0.700 / 0.778) |
| **CRMA** (scenario → dispute outcome) | 25 scenarios | fully-correct share | **0.560** (14/25) |
| **OCR WER/CER** | 15 reference/hypothesis pairs | corpus WER / CER | 0.381 / 0.089 — **utility check only, see below** |
| **DawaCheck mapping** | 52 queries vs a 7-drug table | mapping accuracy | **0.865** (45/52); mapping P/R/F1 0.909 / 0.857 / 0.882 |
| **Appeal completeness** (#107) | the 25 CRMA scenarios x en/hi/mr = 75 BimaNyay GRO letters | weighted checklist score | **0.888** mean (max reachable 0.900, see section 7); 0/75 fully complete |
| **Letter grounding** (#115) | 18 labelled letters (detector) + 225 BimaNyay drafts | hallucination rate / grounding score | drafts **0 / 1,484 claims ungrounded** (template check, see section 8); detector P/R 1.000 / 0.882 |

## 1. BMA — Benchmark Mapping Accuracy
Scored on the production matcher (`_match_cghs_key` in the BillNyay endpoint — the same
longest-substring logic the audit uses) against the 27-entry `cghs_rates.json`. Gold = the
acceptable keys for a line (`[]` = no counterpart exists, and the matcher must not map it).

| Outcome | Rows | Meaning |
|---|---|---|
| correct | 55 | right key, or correctly left unmapped |
| missed | 14 | a counterpart exists, line left un-benchmarked (safe) |
| false_match | 8 | no counterpart, but a rate was applied |
| wrong_key | 1 | a *different* key's rate was applied |

| Category | Rows | Correct |
|---|---|---|
| exact table wording | 16 | 16 |
| table term inside a longer line ("MRI Brain Plain") | 21 | 20 |
| case/format variants | 5 | 5 |
| hospital synonyms/abbreviations ("USG", "Xray", "Angioplasty (PTCA)") | 14 | 0 |
| no counterpart | 12 | 10 |
| hard negatives (look similar to a key) | 10 | 4 |

**Findings**
1. Mapping works when the line contains the table's own wording and fails on every synonym
   or abbreviation (0/14 in that group): there is no synonym handling. These fail *safe*
   (the line is "not benchmarked").
2. **Real defect: substring matching can apply an unrelated rate.** `ppe` is a substring of
   "a**ppe**ndectomy", so *Lap Appendicectomy*, *Appendectomy (Open)* and *Endoscopy Upper GI*
   (via "u**ppe**r") resolve to the PPE-kit rate (₹650/shift); "Particular Care Charges" and
   "Meticulous Dressing Charges" resolve to `icu` (**icu** inside "part**icu**lar"). Whether this
   reaches a patient depends on the quantity rule in `rate_basis` (per-shift/per-day rates
   need a stated count), but "Appendectomy (Open)" with `x 2` would be benchmarked against PPE.
   Not fixed in this PR (harness scope) — see follow-ups.
3. "Dialysis Catheter Insertion", "MRI Contrast Agent", "Consultation Report Copy Fee" and
   "Cataract Surgery Follow-up Drops" map to the parent procedure's rate; a modifier word
   that changes what is being billed is invisible to the matcher.

## 2. PEA — Procedure Extraction Accuracy
`kadi.extraction.run_heuristic_extraction_fallback` on 28 invented plain-text bills (clean,
₹/Rs/INR prefixes, medicines, metadata noise, decimals, OCR spacing, short clinical terms,
quantities, a Devanagari header, and four deliberately awkward layouts). A predicted line
counts only if **name and amount** both match.

| Items | Gold | tp | fp | fn | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| procedures | 61 | 57 | 3 | 4 | 0.950 | 0.934 | 0.942 |
| medicines | 11 | 11 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| all items | 72 | 68 | 3 | 4 | 0.958 | 0.944 | 0.951 |

Stated grand total extracted exactly: 28/28. Procedure-vs-medicine mis-filing: 0.
Two of 28 bills contain any error, both in categories built to be hard:

- **Hyphen separator** (`Consultation - 400`): the parser keeps the trailing hyphen in the
  name (`consultation -`) and also parses `Total - 1900` as a line item (3 fp, 2 fn).
  A `Total` row parsed as a charge would double-count the bill.
- **Trailing text after the amount** (`Consultation: 500 (paid)`): both lines dropped (2 fn).

All 26 other bills — including `Date: 2024-01-15`, Aadhaar/contact lines, `Dolo 650: 33`, and
Indian digit grouping `1,25,000` — were extracted exactly. Heuristic-path only; the Groq
extraction path is unmeasured.

## 3. Billing-anomaly precision / recall / F1
`audit_billing_lines` (extracted from `build_case_audit`, behaviour unchanged) on 39 bills /
70 lines. Positive = a line that should be flagged (overcharged vs rate × stated count, or
a bundled item billed separately).

| Level | tp | fp | fn | tn | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| line | 17 | 2 | 6 | 45 | 0.895 | 0.739 | 0.810 |
| bill (any line anomalous) | 14 | 2 | 6 | 17 | 0.875 | 0.700 | 0.778 |

- All 15 plainly overcharged lines and both bundled lines were flagged; none of the 32 clean
  lines was flagged.
- **All 6 false negatives were abstentions** (`not_benchmarked`), none a wrong "fair" verdict:
  two lines with a recurring rate and no stated count (`Ward Stay 9000`, `Consultation 1200` —
  the auditor refuses to guess), and four hospital synonyms (*Sonography*, *CT-Scan Head*,
  *X Ray Chest*, *Haemodialysis Session*) — the same synonym gap as BMA.
- **2 false positives**: *Ultrasound Guided Biopsy* (matched to the ₹700 ultrasound rate) and
  *Dialysis Catheter Insertion x 1* (matched to the ₹1,800 dialysis session) — the BMA
  substring weakness turned into a wrong "overcharged" flag.

Recall is capped by deliberate abstention. Gold labels for lines outside the 27-entry table
are "not anomalous" because an overcharge cannot be established from the table — which also
means this harness cannot measure how many real overcharges fall outside the table.

## 4. CRMA — Claim-Rejection Mapping Accuracy
BimaNyay's `audit_claim_denial` + `assess_clinical_review_need` on 25 invented repudiation
scenarios. A scenario is correct only if (a) `is_wrongful` matches, (b) where the gold names
one, a returned violation cites the expected clause, and (c) the clinical-review flag
matches. **Labels are the team's reading of the IRDAI 29-May-2024 Master Circular, not legal
advice and not lawyer-verified.**

**CRMA = 0.560 (14/25).** Wrongful-denial P/R/F1 = 0.667 / 0.706 / 0.686 (tp 12, fp 6, fn 5, tn 2);
clause-citation accuracy 0.833 (10/12 checks); clinical-review flag accuracy 1.000 (25/25).

| Group | Scenarios | Correct |
|---|---|---|
| moratorium (PED, policy ≥ 5 y) | 4 | 4 |
| PED under 5 y | 3 | 1 |
| proven fraud | 1 | 0 |
| investigation-only | 4 | 3 |
| room-rent | 2 | 1 |
| delayed intimation | 4 | 3 |
| general exclusion | 4 | 2 |
| category mis-filed (PED reason under `EXCLUSION_CLAUSE`) | 1 | 0 |
| out-of-contract category strings (`PRE-EXISTING`, `ROOM RENT CAPPING`) | 2 | 0 |

**Findings.** The engine decides **only from the category string and policy age; it never reads
the insurer's reason text.** Consequences, each visible in the failures:
1. Every denial in a rule-covered category is called wrongful, even when the stated reason
   is documented and valid (a pre-policy prescription, a genuine investigation-only stay, a
   room-only deduction the policy allows, a forged proposal). 6 false positives.
2. A wrongful denial filed under `EXCLUSION_CLAUSE` or under a category spelling outside the
   five documented ones is never flagged (5 false negatives) — including a PED denial in
   year 7 filed as a general exclusion.
3. The clinical-review flag (regex over the reason + category) matched all 25 labels, but the
   labels for it were also mine and the patterns are simple.

## 5. OCR WER / CER — utility only
`evaluate_ocr` computes corpus WER/CER (total edits ÷ total reference length). **The 15
hypotheses are hand-written simulated errors, not output of any OCR engine**, so the
measured corpus WER 0.381 / CER 0.089 validates the utility and shows how the two metrics
react to error types — it says nothing about Kadi's real OCR accuracy.

| Injected error | WER | CER |
|---|---|---|
| identical | 0.000 | 0.000 |
| digit error | 0.250 | 0.040 |
| dropped line | 0.286 | 0.298 |
| Devanagari matra | 0.286 | 0.053 |
| character substitution | 0.385 | 0.095 |
| dropped characters | 0.500 | 0.057 |
| Devanagari dropped chars | 0.500 | 0.133 |
| merged words | 0.667 | 0.067 |
| split word | 1.000 | 0.062 |

Reading: one wrong character costs a whole word, so WER overstates small glitches while CER
stays low; a dropped line is the one case where CER is large. To score a real OCR engine,
pass its output as `evaluate_ocr(rows, hypotheses={id: text})` against the fixture references
(or add real references) — no OCR run is part of this PR.

## 6. DawaCheck price-mapping accuracy
`benchmark_medicine` on 52 invented queries against the **7-formulation** curated NPPA
subset in `reference_data.py` (so this measures matching behaviour on a tiny table, not
coverage of the real NPPA schedule). Gold written from general pharmaceutical knowledge;
brand→generic claims are not verified against a brand database.

| Outcome | Rows |
|---|---|
| correct | 45 |
| missed (expected a drug, got None — safe) | 4 |
| false_match (not in subset, but mapped) | 2 |
| wrong_drug | 1 |

Per-unit ceiling correct on 29/30 correctly-mapped rows with a gold ceiling (0.967).

| Category | Rows | Correct |
|---|---|---|
| alias, format, dosage variant, spelling/OCR variant | 29 | 29 |
| not in subset | 10 | 10 |
| unlisted brand of a listed drug | 6 | 1 |
| hard negatives (combinations, look-alikes) | 7 | 5 |

**Findings.** Aliases, formats, strength variants (ceiling scaled proportionally) and
spelling/OCR variants all resolved. The failures:
- Genuine brands not in the alias list (*Azee 500, Pantop 40, Zithromax 500, Amoxyclav 625*)
  are missed — safe.
- ***Amoxicillin Clavulanate 625* maps to plain `Amoxicillin 500mg`** (a different, cheaper
  drug's ceiling) via the phonetic path — the dictionary order makes the amoxicillin entry win.
- **Combination products map to a single ingredient**: *Paracetamol + Ibuprofen* →
  Paracetamol 650mg, *Pantoprazole + Domperidone* → Pantoprazole 40mg (both fuzzy-phonetic).
- *Dolo 500* maps to the 650 mg entry through the phonetic path without strength scaling
  (ceiling ₹2.30 vs ₹1.77 if scaled), so the dosage rule does not run on this path.

## 7. Appeal completeness (#107)
`appeal_completeness.py` scores the BimaNyay Level-1 GRO appeal letter (`analyze_insurance_denial`,
the production drafting path) on the issue's weighted checklist — Patient Details 15 %,
Policy Info 20 %, Clauses 30 %, Justification 25 %, References 10 % — for the 25 CRMA scenario
inputs in English, Hindi and Marathi (75 letters; no new labels, each check is made against the
facts the draft was built from). Inside a category every applicable check weighs the same; a
category with nothing applicable (`clauses` when the audit cites no violation) is dropped and
the remaining weights renormalised, so a letter is not penalised for a citation that does not exist.

| Category | Checks | Pass rate |
|---|---|---|
| patient (15 %) | diagnosis stated, both amounts stated, policyholder name filled | 0.667 |
| policy (20 %) | policy number, insurer named, claim reference filled, insurer's reason quoted | 0.750 |
| clauses (30 %) | each audit violation's clause **and** statute appear in the letter | 1.000 |
| justification (25 %) | grounds stated, relief amount restated, 15-day window demanded | 1.000 |
| references (10 %) | Master Circular cited, its date cited, Bima Bharosa **and** Ombudsman named | 1.000 |

**Mean score 0.888; the score is identical across the three languages.**

**Findings.**
1. **Two checks fail on all 75 letters, by design:** the templates leave `[POLICYHOLDER NAME]`
   (and its Hindi/Marathi equivalents) unfilled — the app is bring-your-own-document and does
   not collect the name — and carry no claim number (`Claim No. [CLAIM_NO]` in English; no claim
   number field at all in Hindi/Marathi, because `ClaimDenialInput` has no such field). The best
   score a letter can reach today is therefore **0.900**, and `fully_complete_share` is 0.0. This is
   a disclosed gap (the patient must fill these before sending), not a template bug.
2. **6 letters cite an `UNVERIFIED` clause** (the two room-rent scenarios x 3 languages). They
   score full marks on `clauses` because the auditor *does* put its citation in the letter, but
   the citation says "UNVERIFIED — no primary-source citation". Completeness is not correctness;
   the harness reports the count (`unverified_clause_citations`) rather than hiding it.

**What this does not measure:** legal correctness, tone, whether a cited provision supports the
ground, Hindi/Marathi language quality, the Ombudsman and Bima Bharosa drafts (only the GRO
letter is scored), or the BillNyay (Groq) appeal letter.

## 8. Hallucination rate and grounding score (#115)
`grounding.py` extracts **checkable claims** from a letter — amounts (₹/INR/Rs), the policy number,
clause/section/rule references, percentages, day counts, dates (English, Hindi and Marathi
months; Devanagari digits), and clinician assertions ("Dr. X", "the treating physician certified")
— and checks each against an allowed set built from the facts of the letter's own case (denial
input and audit result) plus a small static reference (`STATIC_REFERENCE`: the Master Circular date,
Bank Rate + 2 %, the 15-day window, Rule 14(1)(b)). A clinician claim can never be grounded
(ADR-011: the system never supplies a named clinician's opinion).

    grounding score    = grounded claims / extracted claims
    hallucination rate = ungrounded claims / extracted claims        (= 1 - grounding score)

"Ungrounded" means **not in the source**, not "false": a real statute such as Section 45 is
ungrounded in a letter whose facts do not cite it (dataset row LG-05). The static reference is the
team's own statement of what the templates assert, **not independently verified law**.

**(a) The BimaNyay drafts: 0 ungrounded of 1,484 claims** (225 documents = 25 scenarios x en/hi/mr
x GRO letter, Bima Bharosa summary, Ombudsman statement; 525 amounts, 300 policy numbers, 96
clauses, 206 percentages, 168 day counts, 189 dates). Hallucination rate 0.000 and grounding score
1.000 meet the issue's targets (< 2 %, > 95 %). **Read this carefully:** these letters are
filled templates, so a clean result is close to guaranteed. It is a regression check — a template
edit that changes a deadline, rate or date, or a field wired to the wrong value, makes it fail
(unit-tested) — **not** evidence about LLM-written letters.

**(b) The detector, validated on 18 hand-written letters with injected hallucinations**
(`letter_grounding_synthetic.jsonl`; wrong amount, wrong policy number, invented/real-but-unsourced
clause, wrong percentage, deadline and date, a clinician assertion, Hindi and Marathi cases,
repeated claims, clean traps): **precision 1.000, recall 0.882 (tp 15, fp 0, fn 2)**. The two misses
are documented limits, kept in the dataset on purpose: an amount written in words (LG-17) and a
case-law citation (LG-18). Four clean letters, including Indian digit grouping and a figure quoted
from the insurer's own reason, produce no false alarm.

**What this does not measure:** the Groq-written letter path (the barrister agent is not run
offline, there is no labelled LLM output, and no live run exists — so **no hallucination figure
exists for LLM letters**); claims the extractor cannot see (words, case law, free-text assertions
of fact); legal correctness. To score an LLM letter, call `ground_letter(text, facts)` on it.

## Limitations (all datasets)
- Synthetic, small (15–78 rows), written by the same team that wrote the code; hard cases are
  over-represented. These are development-set figures, not estimates of production accuracy.
- One gold error was found and corrected during development (PEA-009: the line
  `Dolo 650: 33` is a real medicine charge that the first draft omitted from the gold list).
  No other label was changed after the first run.
- No confidence intervals; with n this small a single row moves a rate by 1–4 points.
- PEA covers only the heuristic extractor; BMA/anomaly only the 27-entry CGHS table; DawaCheck
  only 7 formulations; CRMA labels are unverified legal reading; OCR numbers are simulated.
- Not covered: LLM-path extraction quality, real scanned documents, real OCR WER/CER, CFMA, LLM-written letters (no hallucination figure for them).
- Not built because the system has nothing to score: #105 (policy-clause retrieval), #110 (MRR) and #111 (RAG precision/recall) assume retrieval or ranking; SchemeSetu is rule-based (no RAG, no ranking) and DaaviSetu has no retrieval step. #112 (CRR/DPR) needs a definition of a "context request" first.

## Follow-ups surfaced by the measurements (not done here)
1. BillNyay matcher: whole-word matching (fixes `ppe`⊂appendectomy, `icu`⊂particular) and a
   small synonym table (USG/sonography, Xray, PTCA, haemodialysis...).
2. Kadi line-item parser: tolerate a hyphen separator and trailing text after the amount; make
   `Total - N` a summary line.
3. BimaNyay: use the denial reason text (e.g. documented evidence, proven fraud), don't treat
   all rule-covered categories as wrongful, and normalise category spellings.
4. DawaCheck: match a combination product to a combination entry or refuse; avoid phonetic
   matches that skip the dosage rule. (Touches `reference_data.py` / `checker.py`, which open
   PRs #145/#150 also modify.)

## Regression gate (CI) — added in Wave 1 / WS2 (ADR-024)
The numbers above are now locked in by a gate. `apps/api/app/evaluation/regression.py`
extracts 25 headline metrics (BMA accuracy and mapping F1; PEA procedure/medicine/all-item F1
and total-amount accuracy; anomaly line- and bill-level F1; CRMA, wrongful-denial F1, clause
and clinical accuracy; OCR corpus WER and CER, where lower is better; DawaCheck accuracy,
mapping F1 and ceiling accuracy; appeal mean score and the clauses / justification / references pass rates; grounding score, hallucination rate and detector precision/recall) plus the 10 dataset sizes, and compares them with the
committed baseline `apps/api/app/evaluation/baseline/phase4_baseline.json`.

```bash
python scripts/check_eval_regression.py                 # run harnesses, compare (exit 0/1/2)
python scripts/check_eval_regression.py --current out.json
python scripts/evaluate_phase4.py --check-baseline      # the usual report, then the gate
python scripts/check_eval_regression.py --write-baseline apps/api/app/evaluation/baseline/phase4_baseline.json
```

- **What it measures:** exactly what this document measures — the offline heuristic/rule
  paths on the synthetic datasets. It is a regression gate, **not** an LLM-accuracy or
  real-world-accuracy measurement, and it never calls Groq.
- **Tolerance 0.0 for every metric:** the harnesses are deterministic offline code on fixed
  data, so a re-run reproduces each figure exactly (1e-9 float slack only). Any drop fails;
  an improvement passes and is reported so the baseline can be raised. A changed dataset size
  fails until the baseline is regenerated in a reviewed commit.
- The committed baseline was generated from `python scripts/evaluate_phase4.py --json` on
  2026-11-18 (branch `ws2/llm-reliability`, base a3fffaa) and reproduces the figures in the
  Summary table above (BMA 0.705, PEA procedure F1 0.942, anomaly line F1 0.810, CRMA 0.560,
  OCR WER/CER 0.381/0.089, DawaCheck 0.865).
- CI: the `eval-regression-gate` job in `.github/workflows/ci.yml`; `ci-gate` requires it.
- The LLM extraction path is still unmeasured: there is no labelled LLM dataset and no live
  run; no live-LLM evaluation script is provided, deliberately, so no unmeasured number exists.
