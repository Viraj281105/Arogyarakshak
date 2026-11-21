# Wave 2 handoff: stream D (localised letters, injection v2, terminology CI)

Branch `wave2/d-letters`. Details and numbers: `docs/evaluation/localised-letters.md`.

## What shipped
* `bimanyay.catalogue` (grounds, violation text, statute/clause names; 5 denial categories x en/hi/mr);
  `audit_claim_denial(input, language="en")`; `analyze_insurance_denial` passes the language on.
  English output byte-identical (golden `packages/bimanyay/tests/golden_en_letters.json`).
* `kadi.injection`: Cyrillic/Greek lookalike folding in `_matching_view`.
* `data/evaluation/injection_redteam_synthetic.jsonl` (109 attacks, 102 benign, synthetic) and
  `packages/kadi/tests/test_injection_redteam.py` (reports measured rates; conservative floors).
* `.github/workflows/ci.yml`: report-only `terminology-audit` job (appended at the end; `ci-gate` untouched).
* All hi/mr text is UNREVIEWED: `NEEDS NATIVE-SPEAKER QA`.

## Decisions
* `UNVERIFIED` stays Latin in the hi/mr room-rent clause reference (the appeal harness counts it).
* No "डॉक्टर"/"डॉ" in grounds (grounding harness treats it as an ungroundable clinician claim).
* Paraphrased and most romanised-Hindi attacks are NOT detected; folding is the only detector change.

## Wiring the integrator must add
* None required. No env vars, no schema change, no baseline change (appeal, grounding and crma
  outputs are unchanged; `check_eval_regression.py` passes). Optionally mention the new job and
  corpus in PROJECT_CONTEXT.md / CHANGELOG.md (not edited here by rule).
* Possible merge conflict: none expected; this stream only touched `packages/bimanyay/**`,
  `packages/kadi/kadi/injection.py`, its tests, the corpus, the end of `ci.yml`, two docs.

## Unverified
* hi/mr wording by a native speaker; the CI job on GitHub; the red-team rates against real attackers.
