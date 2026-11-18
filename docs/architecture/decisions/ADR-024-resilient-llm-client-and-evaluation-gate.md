# ADR-024: Resilient LLM client and offline evaluation regression gate

## Status
Accepted (2026-11-18, Wave 1 / WS2). Design note: `docs/superpowers/specs/2026-11-18-ws2-llm-reliability-design.md`.

## Context
Two places called Groq with raw `urllib`: BillNyay's `GroqClient` (every BillNyay agent) and
`kadi.extraction.extract_entities_from_text`. Each made one attempt with a fixed timeout and
fell back to an offline path on any failure. There was no retry for a transient 429/5xx, no
protection when Groq is down (every request still waited for its timeout), no way to name a
second model, no cost bound for the multi-call BillNyay pipeline, and no telemetry hook. The
Phase-4 evaluation harnesses existed but nothing stopped a change from silently lowering
their numbers.

## Decision
1. **One client, in Kadi.** `packages/kadi/kadi/llm/` (`ResilientLlmClient`) performs every
   Groq chat call. Kadi is the shared layer (AGENTS.md) and must not import `apps/api`, so
   its settings are a small dataclass read from the environment (`LlmConfig.from_env`), and
   call sites pass the API key and `GROQ_MODEL` from the API's own settings. Transport stays
   stdlib `urllib` (same URL, headers and payload as before); no dependency added.
2. **Failure handling.** Timeouts, connection errors, 429 and 408/5xx are retried with
   equal-jitter exponential backoff (default 3 attempts, 0.5 s base, 8 s cap). A 429's
   `Retry-After` (delta-seconds or HTTP-date) raises the wait, clamped by
   `LLM_RETRY_AFTER_MAX_SECONDS` (30 s). Other 4xx and malformed 200 bodies are not retried.
   A per-model, process-wide **circuit breaker** (closed → open after 5 consecutive
   availability failures → half-open after 30 s, one probe) short-circuits calls while Groq
   is unhealthy. A non-retryable 4xx proves the provider is reachable and does not open it.
   **429s do count as availability failures**: sustained rate limiting means further calls
   would only add load and wait, and the breaker turns that into a fast offline fallback
   until the probe succeeds. Breaker state is lock-protected (the sync LLM code runs on the
   threadpool) and generation-guarded: every trip/close bumps a generation, and a result
   from a call that started in an older generation is ignored, so a late success cannot
   close an OPEN breaker and a late failure cannot clear the half-open probe.
   **Overall deadline** `LLM_TOTAL_DEADLINE_SECONDS` (default 20 s, must be > 0): one
   monotonic deadline per call across all attempts, backoff sleeps and the fallback model;
   each attempt's timeout is capped to the remaining time, no sleep crosses it, and the
   fallback model is skipped when no time remains (the caller gets the same typed error as
   for exhausted retries and uses its offline fallback). **Per-attempt timeout** =
   `min(call-site timeout, LLM_TIMEOUT_SECONDS)` when that variable is set, else the call
   site's own (BillNyay 12 s, extraction 10 s).
3. **Optional fallback model** `GROQ_FALLBACK_MODEL`, tried after the primary fails
   (including an open circuit). Never hard-coded; deprecated names (ADR-004) and a value equal
   to the primary are ignored.
4. **Token budget per BillNyay pipeline run** `LLM_CASE_TOKEN_BUDGET` (0 = unlimited, the
   default). BillNyay's `llm_client()` creates one budget per pipeline run (one appeal or
   grievance draft); a call whose conservative estimate (`ceil(chars/4) + max_tokens`) does
   not fit raises `BudgetExceeded` before any network call, and the agent's existing canned
   fallback takes over. **Known gap (follow-up):** this is not a lifetime per-case budget —
   drafting again for the same case starts a fresh budget, and Kadi extraction is not
   budgeted — because keying a ledger by case id would put case ids into LLM-layer state; a
   real per-case budget needs a design that stores only a fingerprint. `ensure_fits` and
   `charge` are separately locked, not one atomic step: two concurrent calls on the same
   budget can both pass the check and overshoot by at most one call's usage. BillNyay's
   agents run sequentially, so this is accepted.
5. **The client never invents text.** It returns a model response or raises a typed
   `LlmError`. Every call site keeps its existing offline fallback (`GroqClientFallback`, the
   heuristic extractor), and `used_fallback` keeps its meaning.
6. **Observer hook** (`kadi/llm/observer.py`, interface agreed with WS1): one
   `LlmCallEvent(model, kind, outcome, latency_s, prompt_tokens, completion_tokens, cache_hit,
   retries, circuit_state)` per call. No prompt or response text: the only string fields are
   the configured model and three validated, enumerated labels.
7. **Prompt versions and shadow runs.** A `PromptVersion` registry labels prompts (Kadi
   extraction's version is the hash of its template). An opt-in `ShadowRunner`
   (`LLM_SHADOW_*`) runs a candidate model/prompt beside production and keeps only counters
   and an agreement score.
8. **Offline regression gate.** `scripts/check_eval_regression.py` compares the harness
   metrics with `apps/api/app/evaluation/baseline/phase4_baseline.json` (tolerance 0.0: the
   harnesses are deterministic) and fails CI (`eval-regression-gate` job) on any drop or a
   dataset-size change. It measures the offline heuristic/rule paths on synthetic data, not
   LLM accuracy.

## Zero retention and the response cache (ADR-003, ADR-010)
The cache is **off by default** (`LLM_CACHE_ENABLED=false`). When enabled it is an in-memory
LRU (default 256 entries) with a short TTL (default 300 s), never persisted, lost on restart.
Keys are SHA-256 digests of (model, prompt version, redacted system and user text, sampling
parameters); the cache refuses any key that is not a digest. Only `temperature == 0`
requests whose text `kadi.redaction.redact_pii` leaves **unchanged** are cached: keying on
the redacted text of an input that contained identifiers would let two bills differing only
in the patient name share an entry and serve one patient's extracted name to another. Raw
OCR text nearly always carries a labelled name, so most extraction calls bypass the cache;
that is intended. Shadow runs use the same "redaction is a no-op" rule.

**Residual risk, accepted only while the cache stays off by default:** a cached *value* is
model output derived from document text. `redact_pii` removes direct identifiers only (names
in labelled fields, phone, Aadhaar, ABHA, PAN, email), not all PHI, so a value can still hold
a diagnosis, an unlabelled name or other re-identifying content for up to the TTL. Mitigations:
bounded size, short TTL, memory only, no case id stored, and `purge()` — called by
`app.services.case_purge.purge_case` on every case erasure (client `DELETE`, retention sweep,
demo reset). Because the cache holds no case id the purge clears the whole cache. A call that
is still in flight while a case is erased can insert its result **after** `purge()`; that
entry lives at most one TTL (default 300 s) and is evicted then. Enabling the cache in a real
deployment is an operator decision that should be recorded.

## Tests never reach the network
The CI backend job used to set `GROQ_API_KEY: mock_test_key_for_ci`, so unpatched appeal
tests sent real requests to api.groq.com (rejected, then the canned fallback). That line is
removed. `apps/api/tests/conftest.py` and `packages/kadi/tests/conftest.py` clear the key
(settings and environment) for every test and replace `urllib.request.urlopen` with a guard
that raises `RuntimeError("live network calls are forbidden in tests")`; tests that exercise
the live-client path inject a fake transport or patch `urlopen` themselves.

## Consequences
- Transient Groq errors are retried instead of immediately degrading to templates; when Groq
  is down, requests fall back in milliseconds instead of waiting for a timeout each.
- Worst-case latency before a fallback is bounded by `LLM_TOTAL_DEADLINE_SECONDS` per call
  (20 s by default, versus 10–12 s for the old single attempt). A BillNyay run makes several
  sequential calls, but once Groq is down the breaker opens after 5 failures and the rest
  fall back immediately. `LLM_MAX_ATTEMPTS=1` restores the old single attempt.
- Breakers and the cache are per process; that matches ADR-019 (exactly one API process).
- Retry/breaker behaviour has only been tested against fakes; it has not been observed against
  the real Groq service in this change.
- A change that lowers any harness metric now fails CI until the baseline is lowered in a
  reviewed commit, which makes every trade-off explicit.
