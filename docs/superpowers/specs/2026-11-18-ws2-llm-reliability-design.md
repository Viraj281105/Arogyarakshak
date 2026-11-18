# WS2 — LLM reliability + CI evaluation gate: design note

**Date:** 2026-11-18 · **Branch:** `ws2/llm-reliability` · **Plan:** `docs/superpowers/plans/2026-11-18-wave1.md` (WS2)
**ADR:** ADR-024 (written with the implementation).

## 1. What exists today
Two places speak raw HTTP to Groq, both with `urllib.request.urlopen`, synchronously, one
attempt, then an offline fallback:

| Call site | Timeout | Offline fallback | How it is invoked |
|---|---|---|---|
| `apps/api/app/services/billnyay_llm.py::GroqClient.generate` (used by every BillNyay agent: Auditor, Clinician, Barrister) | 12 s | `GroqClientFallback` canned per-agent text, `used_fallback = True` | sync, from `run_in_threadpool` in `services/billnyay_appeal.py` |
| `packages/kadi/kadi/extraction.py::extract_entities_from_text` | 10 s | `run_heuristic_extraction_fallback` | sync, from `run_in_threadpool` in `services/case_ingestion.py` |

`billnyay/agents/barrister.py` does not call Groq itself: it calls the injected
`client.generate(...)`, so migrating `GroqClient` migrates it (no edit needed there).
`case_ingestion.py`, `billnyay_appeal.py` and `clinical/demo_control.py` only pass settings or
read `settings.groq_api_key`. No other raw Groq call exists (grep for `urlopen`,
`api.groq.com`, `httpx`).

Concurrency model: one API process (ADR-019), async endpoints, the sync LLM code runs on
Starlette's threadpool, so several threads may call the client at once. Shared state
(breakers, cache, budget, observers, shadow counters) is therefore guarded by locks.

## 2. Client API (`packages/kadi/kadi/llm/`)
Kadi is the shared layer and must not import `apps/api`; the API passes its settings in.

```python
client = ResilientLlmClient(api_key=settings.groq_api_key, model=settings.groq_model)
resp = client.complete(LlmRequest(system=..., prompt=..., kind="kadi.extraction",
                                  prompt_version=KADI_EXTRACTION_PROMPT, temperature=0.0,
                                  max_tokens=1024, json_mode=True, timeout_s=10.0,
                                  budget=None))
resp.text, resp.model, resp.prompt_tokens, resp.completion_tokens, resp.cache_hit, resp.retries
```
`complete()` raises a typed `LlmError` subclass on failure; it never returns canned text.
Call sites keep their own offline fallbacks by catching `Exception` exactly as before.

Process-wide state lives in an `LlmRuntime` (breaker registry, optional cache, optional
shadow runner, transport, clock, sleep, seeded RNG). `default_runtime()` builds it lazily
from the environment (`LlmConfig.from_env()`); tests inject their own with
`set_default_runtime(...)` / `reset_default_runtime()`. Breakers must be process-wide
because `GroqClient` is instantiated per request.

Transport: stdlib `urllib.request.urlopen` (looked up at call time, so existing tests that
patch it keep working unchanged), same URL and same JSON payload shape as before
(`response_format` only when `json_mode`). No new dependency.

## 3. Retry classification and backoff
| Error | Class | Retried | Counts toward breaker |
|---|---|---|---|
| socket timeout / `TimeoutError` | `LlmTimeout` | yes | yes |
| connection failure (`URLError`) | `LlmConnectionError` | yes | yes |
| HTTP 429 | `LlmRateLimited` (honours `Retry-After`, capped) | yes | yes |
| HTTP 408, 5xx | `LlmServerError` | yes | yes |
| other HTTP 4xx (401, 400, 404 ...) | `LlmClientError` | no (next model, if any) | no — provider reachable |
| 200 with a malformed body | `LlmResponseError` | no | no |

Backoff for retry *n* (0-based): `cap = min(max_delay, base * 2**n)`, `delay =
rng.uniform(cap/2, cap)` ("equal jitter": never zero, never above the cap). For 429,
`delay = min(max_delay, max(delay, Retry-After))`. Sleep and RNG are injected; tests use a
recording sleep and `random.Random(seed)`. Defaults: 3 attempts, base 0.5 s, max 8 s.

## 4. Circuit breaker
One breaker per model, shared by the process. `closed` → after `failure_threshold`
consecutive breaker-counted failures → `open` (calls rejected with `LlmCircuitOpen`, no
network) → after `recovery_seconds` on the injected clock → `half_open`, which admits exactly
one probe; probe success → `closed`, probe failure → `open` again (timer restarts). A
non-breaker outcome (e.g. 401) counts as "reachable" and closes it. All transitions under a
`threading.Lock`. When the primary's breaker is open the fallback model (if configured) is
tried; it has its own breaker. Defaults: threshold 5, recovery 30 s.

## 5. Fallback model
`GROQ_FALLBACK_MODEL` (default empty = none). Never hard-coded. A deprecated name (ADR-004
list) or a value equal to the primary is ignored with a warning. Tried only after the
primary failed (any error, including an open circuit). A success there reports outcome
`fallback`.

## 6. Token budget
`TokenBudget(limit)` is per pipeline run: `llm_client()` creates one per BillNyay drafting
request (= one case), so every agent call for that case draws from it. Before a call the
client reserves a conservative estimate `ceil(chars/4) + max_tokens`; if it does not fit,
`BudgetExceeded` is raised **without a network call**, and the call site's offline fallback
takes over (behaviour preserved, outcome `budget_exceeded`). After a success the actual
`usage.total_tokens` (or the estimate if absent) is charged. `LLM_CASE_TOKEN_BUDGET=0`
(default) = unlimited, i.e. no behaviour change. Kadi extraction is one bounded call
(≤ 6000 chars in, 1024 tokens out) and is not budgeted. The budget holds no case id.

## 7. Response cache (off by default) and zero retention
- Off unless `LLM_CACHE_ENABLED=true`; in-memory `OrderedDict` LRU, bounded
  (`LLM_CACHE_MAX_ENTRIES`, default 256), TTL (`LLM_CACHE_TTL_SECONDS`, default 300) on the
  injected clock; never persisted; lost on restart.
- Key = SHA-256 over canonical JSON of `(model, prompt_version, redact_pii(system),
  redact_pii(prompt), temperature, max_tokens, json_mode)`. Keys are 64-hex digests; no raw
  text is ever a key (tested).
- **Eligibility:** only `temperature == 0` requests whose text is *unchanged* by
  `kadi.redaction.redact_pii`. Keying on redacted text alone would be unsafe: two bills that
  differ only in the patient's name would share a key and one patient's extracted name would
  be served to another. Requiring "redaction is a no-op" makes the redacted key equal to the
  full input, so no such collision exists. Raw OCR text almost always carries a labelled
  name, so in practice extraction calls are rarely cached; that is the intended trade-off.
- Residual risk (ADR-024): cached **values** are model outputs and can contain sensitive-
  looking content that `redact_pii` did not recognise (it removes direct identifiers only,
  not all PHI). Hence: off by default, short TTL, bounded, memory only, and `purge()` —
  wired into `app.services.case_purge.purge_case`, which clears the whole cache (the cache
  holds no case id, so a per-case purge is impossible by design).

## 8. Observer hook (WS1 interface)
`kadi/llm/observer.py`: `register_llm_observer(fn) -> unregister`, frozen dataclass
`LlmCallEvent(model, kind, outcome, latency_s, prompt_tokens, completion_tokens, cache_hit,
retries, circuit_state)`. Exactly one event per `complete()`. `outcome` ∈ `ok | error |
timeout | rate_limited | circuit_open | budget_exceeded | fallback`. String fields are only
`model` (from config), `kind` (validated against `^[a-z0-9_.]{1,64}$`, set by code),
`outcome` and `circuit_state` (enumerated). Observer exceptions are logged and swallowed. A
test asserts the str-field set, and a property-style test asserts that sentinel strings
planted in prompts and responses never appear in any event.

## 9. Prompt/model versioning and shadow runs
- `PromptVersion(name, version)` + registry (`register_prompt_version`, `get_prompt_version`,
  `registered_prompt_versions`). `PromptVersion.from_template(name, text)` derives the version
  from a SHA-256 of the template so editing a constant prompt bumps it automatically (used
  for Kadi extraction); BillNyay agent prompts vary per call, so they carry explicit versions.
- `ShadowRunner` (off by default; `LLM_SHADOW_ENABLED`, `LLM_SHADOW_MODEL`,
  `LLM_SHADOW_SAMPLE_RATE`, `LLM_SHADOW_MAX_RUNS`): after a successful production call it
  may run the candidate model (optionally a candidate system prompt registered in code) on
  the same input, only when that input is unchanged by `redact_pii` (same rule as the cache),
  not cached, not budget-charged, not falling back, at most `max_runs` per process (cost
  bound) and only for a sampled fraction. It records numbers only, per `kind`: runs,
  skipped (pii / sampled-out / cap), errors, exact matches, mean agreement (JSON: share of
  equal top-level fields; text: token Jaccard). No content is stored. Runs on a single
  background worker thread so production latency is unaffected; tests run it inline.

## 10. CI evaluation gate
- `apps/api/app/evaluation/regression.py`: a fixed list of headline metrics with a direction
  (`higher`/`lower` is better) plus exact row counts; `extract_metrics(reports)`,
  `compare(baseline, current) -> RegressionReport`, `build_baseline(reports)`.
- Baseline committed at `apps/api/app/evaluation/baseline/phase4_baseline.json`, generated
  from `python scripts/evaluate_phase4.py --json` via `scripts/check_eval_regression.py
  --write-baseline`.
- `scripts/check_eval_regression.py` runs the harnesses in-process (or reads `--current
  file.json`), prints a delta table, exits 0 / 1 (regression) / 2 (structural: missing
  metric, non-synthetic dataset, bad baseline). `scripts/evaluate_phase4.py --check-baseline`
  runs the same check.
- **Tolerances:** every harness is deterministic offline code on fixed synthetic data, so run
  to run noise is zero and the tolerance is `0.0` (plus 1e-9 float slack) for every metric;
  any drop fails. Improvements pass and are reported ("update the baseline"). Row counts must
  match exactly (a dataset edit requires a reviewed baseline update). The per-metric
  `tolerance` field exists so a future non-deterministic metric can carry a justified
  non-zero value; changing one is a reviewed edit of the committed file.
- CI: a new small job `eval-regression-gate` appended at the end of `jobs:` (needs
  `governance-and-invariants`), installing only `apps/api/requirements.txt` and the domain
  packages with `--no-deps` (the harnesses import no OCR/torch code); added to `ci-gate`
  `needs` and its status script the way `foundation-checks` was.
- Honesty: the gate measures the **offline/heuristic paths on synthetic data**, not LLM
  accuracy (see `docs/evaluation/phase4-harnesses.md`). The optional manual live-LLM script
  is deliberately not provided: without a labelled LLM dataset and a real run it could only
  produce unmeasured numbers.

## 11. What is not verified here
- No live Groq call is made (no key used); retry/backoff/breaker behaviour against the real
  service and real 429 `Retry-After` values are unverified.
- The CI job itself has not run on GitHub; it is validated by YAML parse, the ci-workflow
  Node test and by running the same commands locally.
- Shadow-run agreement metrics have never been produced on real traffic.
