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
2. **Failure handling.** Timeouts, connection errors, 429 (honouring a numeric
   `Retry-After`) and 408/5xx are retried with equal-jitter exponential backoff (default 3
   attempts, 0.5 s base, 8 s cap). Other 4xx and malformed 200 bodies are not retried. A
   per-model, process-wide **circuit breaker** (closed → open after 5 consecutive
   availability failures → half-open after 30 s, one probe) short-circuits calls while Groq
   is unhealthy. A non-retryable 4xx proves the provider is reachable and does not open it.
   Breaker state is lock-protected: the sync LLM code runs on the threadpool.
3. **Optional fallback model** `GROQ_FALLBACK_MODEL`, tried after the primary fails
   (including an open circuit). Never hard-coded; deprecated names (ADR-004) and a value equal
   to the primary are ignored.
4. **Per-case token budget** `LLM_CASE_TOKEN_BUDGET` (0 = unlimited, the default). BillNyay's
   `llm_client()` creates one budget per pipeline run; a call whose conservative estimate
   (`ceil(chars/4) + max_tokens`) does not fit raises `BudgetExceeded` before any network
   call, and the agent's existing canned fallback takes over.
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
demo reset). Because the cache holds no case id the purge clears the whole cache. Enabling
the cache in a real deployment is an operator decision that should be recorded.

## Consequences
- Transient Groq errors are retried instead of immediately degrading to templates; when Groq
  is down, requests fall back in milliseconds instead of waiting for a timeout each.
- Worst-case latency before a fallback grows from one timeout to `max_attempts` timeouts plus
  backoff (defaults: about 3 × 12 s + 1.5 s for BillNyay). `LLM_MAX_ATTEMPTS=1` restores the
  old single-attempt behaviour.
- Breakers and the cache are per process; that matches ADR-019 (exactly one API process).
- Retry/breaker behaviour has only been tested against fakes; it has not been observed against
  the real Groq service in this change.
- A change that lowers any harness metric now fails CI until the baseline is lowered in a
  reviewed commit, which makes every trade-off explicit.
