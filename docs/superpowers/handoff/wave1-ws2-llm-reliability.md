# Wave 1 — WS2 handoff: LLM reliability + CI evaluation gate

**Branch:** `ws2/llm-reliability` (from `wave1/integration` @ a3fffaa) · **Date:** 2026-11-18
**Design note:** `docs/superpowers/specs/2026-11-18-ws2-llm-reliability-design.md` · **ADR:** ADR-024

## What shipped
1. **Resilient client** `packages/kadi/kadi/llm/` — `ResilientLlmClient.complete(LlmRequest)`:
   per-attempt timeout; equal-jitter exponential retries on timeout / connection / 429
   (numeric `Retry-After` honoured, capped) / 408 / 5xx; per-model process-wide circuit
   breaker (closed/open/half-open, one probe, lock-protected, injectable clock); optional
   `GROQ_FALLBACK_MODEL` (deprecated ADR-004 names and "same as primary" refused); per-pipeline-run
   `TokenBudget` (`BudgetExceeded` before any network call); opt-in in-memory cache
   (off by default, LRU + TTL, SHA-256 keys only, only `temperature == 0` inputs that
   `redact_pii` leaves unchanged, `purge()`); typed errors, never invented text. Settings:
   `LlmConfig.from_env()` (own dataclass; `apps/api/app/config.py` untouched). Transport is
   stdlib `urllib` (same URL/headers/payload as before; no new dependency).
2. **Call sites migrated, behaviour preserved**
   - `kadi/extraction.py`: same payload and 10 s timeout, same heuristic fallback on any
     failure (now also open circuit / exhausted retries). Prompt moved to module constants;
     `KADI_EXTRACTION_PROMPT` is versioned by template hash. Failure log records the exception
     type only.
   - `apps/api/app/services/billnyay_llm.py` `GroqClient`: same payload, 12 s timeout, same
     `GroqClientFallback` text, same `used_fallback`; calls labelled `billnyay.auditor |
     clinician | barrister | generic` with registered prompt versions; new optional
     `token_budget` constructor arg. `llm_client()` creates one budget per pipeline run when
     `LLM_CASE_TOKEN_BUDGET > 0` (default unlimited).
   - `billnyay/agents/barrister.py`: **no change needed** — it calls the injected
     `client.generate()`; migrating `GroqClient` migrates it. No other raw Groq call exists
     (`case_ingestion.py`, `billnyay_appeal.py`, `demo_control.py` only pass/read settings).
   - `app/services/case_purge.py::purge_case` calls `kadi.llm.purge_default_cache()` (the
     cache holds no case id, so erasure clears it all; no-op when disabled).
3. **Observer hook** `kadi/llm/observer.py`: `register_llm_observer(fn) -> unregister`,
   frozen `LlmCallEvent(model, kind, outcome, latency_s, prompt_tokens, completion_tokens,
   cache_hit, retries, circuit_state)`, exactly one event per call; `outcome`, `circuit_state`
   enumerated and `kind` regex-validated on construction; observer exceptions swallowed+logged.
4. **Prompt versions + shadow runs**: `PromptVersion` registry (`kadi/llm/prompts.py`);
   `ShadowRunner` (`kadi/llm/shadow.py`), off by default, PII-free inputs only, sampled,
   capped per process, no cache/fallback/budget, background single worker thread, counters
   and agreement scores only (`runtime.shadow.snapshot()`).
5. **CI evaluation gate**: `apps/api/app/evaluation/regression.py`, committed baseline
   `apps/api/app/evaluation/baseline/phase4_baseline.json` (17 headline metrics with
   direction + 7 dataset sizes, generated from `evaluate_phase4.py --json`, values match
   `docs/evaluation/phase4-harnesses.md`), `scripts/check_eval_regression.py` (exit 0 pass /
   1 regression / 2 structural; `--current`, `--baseline`, `--write-baseline`),
   `scripts/evaluate_phase4.py --check-baseline`. Tolerance 0.0 everywhere (deterministic
   harnesses; 1e-9 float slack). New CI job `eval-regression-gate` appended at the end of
   `jobs:` (needs `governance-and-invariants`, same `@v4/@v5` action tags), added to
   `ci-gate` needs/echo/summary/condition (as a new last continued line). It measures the
   offline paths on synthetic data, **not LLM accuracy**. No live-LLM script was added.
6. **Docs**: ADR-024 (incl. cache residual risk), env vars section 4 in
   `docs/configuration/environment-variables.md`, `.env.example` block, `docker-compose.yml`
   api passthroughs (empty → defaults), `phase4-harnesses.md` gate section, troubleshooting §8,
   one invariant line in `docs/architecture/repository-structure.md`.

## Env vars (all optional; defaults keep old behaviour except retries + breaker)
`GROQ_FALLBACK_MODEL`, `LLM_TIMEOUT_SECONDS` (unset = call-site timeout; set = min(call
site, value)), `LLM_TOTAL_DEADLINE_SECONDS` (20, > 0), `LLM_MAX_ATTEMPTS` (3),
`LLM_BACKOFF_BASE_SECONDS` (0.5), `LLM_BACKOFF_MAX_SECONDS` (8),
`LLM_RETRY_AFTER_MAX_SECONDS` (30),
`LLM_BREAKER_FAILURE_THRESHOLD` (5), `LLM_BREAKER_RECOVERY_SECONDS` (30),
`LLM_CASE_TOKEN_BUDGET` (0 = unlimited), `LLM_CACHE_ENABLED` (false), `LLM_CACHE_MAX_ENTRIES`
(256), `LLM_CACHE_TTL_SECONDS` (300), `LLM_SHADOW_ENABLED` (false), `LLM_SHADOW_MODEL` (""),
`LLM_SHADOW_SAMPLE_RATE` (0.1), `LLM_SHADOW_MAX_RUNS` (50). Read from the **process
environment**, not the API's `.env` (local runs: export or `uvicorn --env-file`).

## Verification (run in D:/wt/ws2 with the shared venv, PYTHONPATH = worktree apps/api + packages; `kadi.__file__` resolved inside D:/wt/ws2)
- `python -m pytest apps/api -q` → **536 passed, 1 skipped** (baseline 499/1).
- `python -m pytest packages/ -q` → **694 passed, 6 skipped** (baseline 612/6).
- `python scripts/ci_guardrails.py` → ALL CHECKS PASSED (exit 0).
- `ruff check apps/api packages --select=E9,F63,F7,F82 --target-version=py311` → All checks passed.
- `PYTHONPATH=apps/api lint-imports` → 5 contracts kept, 0 broken.
- `python scripts/evaluate_phase4.py` → exit 0; `--check-baseline` → exit 0.
- `python scripts/check_eval_regression.py` → `RESULT: PASS`, exit 0. With a deliberately
  degraded copy of the baseline (pea.procedures.f1 raised to 0.99, ocr.corpus_wer lowered to
  0.30) → both rows `REGRESSED`, exit 1.
- Same gate in a **fresh venv with only `apps/api/requirements.txt`** + the four packages on
  PYTHONPATH → PASS (supports the CI job's `--no-deps` install; not the CI run itself).
- `npm ci` + `node --import tsx --test scripts/tests/ci-workflow.test.mjs` → 3 pass, 0 fail
  (it caught a literal `\n` I first wrote into the ci-gate condition; fixed).
- `yaml.safe_load(ci.yml)` → 8 jobs; ci-gate needs include `eval-regression-gate`; extracted
  ci-gate script `bash -n` OK; simulated with all-success → exit 0, eval failure → exit 1.
- `docker compose config --quiet` (and with the demo override) → valid.

### Test-first notes (honest)
Red→green was observed for: primitives (import failure), extraction migration (3 fails),
GroqClient migration (11 fails), cache purge on erasure (1 fail), regression gate (import
failure) and `--check-baseline` (1 fail). The client and shadow tests were written before
the implementation but first run after it (green on first run). Two red runs of the OLD
call-site code sent real requests to `api.groq.com` with the fake key `k` (403) — that is
what the pre-migration code does; the migrated code and all new tests use fake transports.
Existing tests: **none changed** (the urlopen-patching prompt-injection tests pass
unchanged because the transport still calls `urllib.request.urlopen(req, timeout=...)`).
Only addition to shared test infra: an autouse `reset_llm_runtime` fixture in
`apps/api/tests/conftest.py` and a new `packages/kadi/tests/conftest.py`.

## Review fixes (second pass, same day)
Shipped (commits 4c746c0, 136d5d6, fde9cdb, 55ee754):
- **Overall deadline** `LLM_TOTAL_DEADLINE_SECONDS` (default 20, must be > 0; 0/negative/
  non-numeric → warning + default): checked before every attempt, backoff sleep and model
  switch; per-attempt timeout capped to the remaining time; no sleep crosses it; fallback
  model skipped when no time remains; caller gets the same typed error as exhausted retries.
- **Effective timeout** = `min(call site, LLM_TIMEOUT_SECONDS)` when set; unset → call site.
- **Retry-After**: HTTP-date parsed (past date → 0); separate clamp
  `LLM_RETRY_AFTER_MAX_SECONDS` (30), still bounded by the deadline.
- **Breaker generation tokens**: late results from an older generation are ignored.
- **Shadow submit guarded** (exception type logged, production response kept);
  **observer registration idempotent**.
- **`--only X --check-baseline`** gates harness X only (`compare(..., only=...)`).
- **Budget wording** made honest everywhere: per BillNyay pipeline run, extraction unbudgeted
  (follow-up recorded); ADR-024 documents 429-as-availability-failure, non-atomic
  ensure_fits/charge, and the in-flight insert after `purge()` (lives ≤ one TTL).
- **No network in tests**: removed `GROQ_API_KEY: mock_test_key_for_ci` from the backend CI
  job; apps/api conftest adds autouse `no_groq_key` (settings + env cleared) and
  `network_guard` (urlopen raises "live network calls are forbidden in tests" and records the
  URL); kadi tests conftest does the same. New `test_no_live_network.py` proves an unpatched
  appeal draft makes no network attempt. **No existing test relied on the mock key reaching
  the network** — the full suites passed unchanged with the guard in place.
- Existing test changed: `test_llm_primitives.py::test_backoff_honours_retry_after_but_stays_capped`
  (this branch's own test) now expects the 30 s Retry-After clamp instead of 8 s; stale
  docstring in `test_api.py::test_offline_fallback_never_claims_denial_facts_were_extracted`
  updated (comment only).

RED→GREEN evidence (this pass, real runs): `test_llm_review_fixes.py` 13 failed / 2 passed
before the change → 15 passed after; `test_eval_regression.py` new `--only` tests 2 failed →
pass; `test_no_live_network.py` 3 errored (no `network_guard` fixture) → 4 passed.

Verification after the fixes:
- `python -m pytest apps/api -q` → **542 passed, 1 skipped** (baseline 499/1).
- `python -m pytest packages/ -q` → **709 passed, 6 skipped** (baseline 612/6).
- ci_guardrails exit 0; ruff (E9,F63,F7,F82) all passed; lint-imports 5 kept / 0 broken.
- `check_eval_regression.py` → PASS (exit 0); degraded baseline → 2 rows REGRESSED (exit 1);
  `evaluate_phase4.py` exit 0; `--only ocr --check-baseline` exit 0.
- ci-workflow node test 3 pass / 0 fail; ci.yml YAML parses (8 jobs, backend test-step env
  now DATABASE_URL, GROQ_MODEL, MIGRATION_TEST_DATABASE_URL, PYTHONPATH); ci-gate `bash -n` OK;
  `docker compose config --quiet` valid.

## Not verified
- No live Groq call: real retry/breaker/429 `Retry-After` behaviour, fallback-model
  behaviour and token usage accounting against the real API are unverified.
- The `eval-regression-gate` CI job has not run on GitHub.
- Shadow-run agreement metrics have never been produced on real traffic.
- Docker stack not started (only `compose config`).

## Cross-stream / integrator notes
- **WS1 glue**: at API startup call `kadi.llm.register_llm_observer(record_llm_event)` (fields
  match the plan interface exactly; `test_event_type_has_no_free_text_fields` pins the field
  list/order). `kind` label set today: `kadi.extraction`, `billnyay.auditor`,
  `billnyay.clinician`, `billnyay.barrister`, `billnyay.generic`, plus `<kind>.shadow` when
  shadow runs are on. Event models: `GROQ_MODEL`, `GROQ_FALLBACK_MODEL`, `LLM_SHADOW_MODEL`
  values only. Note the apps conftest resets the runtime, **not** observers.
- `ci.yml`: my edits are the ci-gate needs/echo/summary/condition lines and a new job at the
  end; if WS1 also adds a job, both condition lines need ` && \` continuations.
- `docker-compose.yml` (not in the conflict map) gained 15 `api.environment` passthrough
  lines after `SAFETY_RULE_REQUIRED_APPROVALS`.
- CI backend job no longer sets `GROQ_API_KEY` (review ruling); test conftests clear the key
  and guard `urllib.request.urlopen` (see "Review fixes").
- Worst-case latency before a fallback is bounded per call by `LLM_TOTAL_DEADLINE_SECONDS`
  (default 20 s); `LLM_MAX_ATTEMPTS=1` restores the old single attempt.
- `docker-compose.yml` passthrough lines are now 17 (added `LLM_TOTAL_DEADLINE_SECONDS`,
  `LLM_RETRY_AFTER_MAX_SECONDS`).
- `PROJECT_CONTEXT.md` / `CHANGELOG.md` not edited (per plan); fold this note in.

## Follow-ups
- Token budget is per BillNyay pipeline run, not a lifetime per-case budget, and Kadi
  extraction is unbudgeted (review ruling: documented, not keyed by case id). A true per-case
  budget needs a fingerprint-keyed design.
- Wire `runtime.shadow.snapshot()` into WS1 metrics if shadow runs are ever enabled.
- Pre-existing: `kadi.extraction` logs matched prompt-injection phrases (document text
  fragments) at WARNING — outside this stream's scope, worth revisiting under the PHI-in-logs rule.
- A labelled LLM-extraction dataset would be needed before any LLM-accuracy claim.
