"""The resilient Groq chat client (WS2, ADR-024).

One place performs every Groq chat call: timeout, jittered exponential retries on
transient failures, a per-model circuit breaker, an optional fallback model, an optional
per-case token budget, an optional in-memory response cache (off by default), an observer
event per call, and optional shadow runs. ``complete()`` either returns a real model
response or raises a typed ``LlmError``; it never invents text. Call sites keep their own
offline fallbacks by catching the exception exactly as they did before.

Process-wide state (breakers, cache, shadow runner) lives in an ``LlmRuntime``. The API is
a single process (ADR-019) whose sync LLM code runs on the threadpool, so the runtime and
everything in it is lock-protected.
"""

import logging
import random
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from kadi.llm.breaker import CircuitBreaker
from kadi.llm.budget import TokenBudget, estimate_tokens
from kadi.llm.cache import ResponseCache, cache_key, is_cache_eligible
from kadi.llm.config import LlmConfig
from kadi.llm.errors import (
    BudgetExceeded,
    LlmCircuitOpen,
    LlmError,
    LlmNotConfigured,
    LlmRateLimited,
    LlmResponseError,
    LlmTimeout,
)
from kadi.llm.observer import KIND_RE, LlmCallEvent, emit_llm_event
from kadi.llm.prompts import PromptVersion
from kadi.llm.retry import BackoffPolicy, counts_toward_breaker, is_retryable
from kadi.llm.transport import UrllibGroqTransport, classify_transport_error

logger = logging.getLogger("arogyarakshak.kadi.llm")

Transport = Callable[[Dict[str, Any], str, float], Dict[str, Any]]


@dataclass
class LlmRequest:
    system: str
    prompt: str
    kind: str  # code-defined label, e.g. "kadi.extraction" — never user text
    prompt_version: Optional[PromptVersion] = None
    temperature: float = 0.0
    max_tokens: int = 1024
    json_mode: bool = True
    timeout_s: Optional[float] = None
    budget: Optional[TokenBudget] = None


@dataclass(frozen=True)
class LlmResponse:
    text: str
    model: str
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    cache_hit: bool = False
    retries: int = 0
    used_fallback_model: bool = False


class LlmRuntime:
    """Process-wide LLM state and injectable dependencies (transport, clock, sleep, RNG)."""

    def __init__(self, config: Optional[LlmConfig] = None, transport: Optional[Transport] = None,
                 clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep,
                 rng: Optional[random.Random] = None, shadow_executor=None):
        self.config = config or LlmConfig()
        self.transport: Transport = transport or UrllibGroqTransport()
        self.clock = clock
        self.sleep = sleep
        self._rng = rng or random.Random()
        self._rng_lock = threading.Lock()
        self._lock = threading.Lock()
        self._breakers: Dict[str, CircuitBreaker] = {}
        self.backoff = BackoffPolicy(self.config.backoff_base_s, self.config.backoff_max_s)
        self.cache: Optional[ResponseCache] = (
            ResponseCache(self.config.cache_max_entries, self.config.cache_ttl_s, clock)
            if self.config.cache_enabled else None
        )
        self.shadow = None
        if self.config.shadow_enabled and self.config.shadow_model:
            from kadi.llm.shadow import ShadowRunner  # local: shadow imports this module

            self.shadow = ShadowRunner(
                runtime=self, model=self.config.shadow_model,
                sample_rate=self.config.shadow_sample_rate, max_runs=self.config.shadow_max_runs,
                executor=shadow_executor,
            )

    def breaker(self, model: str) -> CircuitBreaker:
        with self._lock:
            b = self._breakers.get(model)
            if b is None:
                b = CircuitBreaker(self.config.breaker_failure_threshold, self.config.breaker_recovery_s, self.clock)
                self._breakers[model] = b
            return b

    def backoff_delay(self, retry_index: int, retry_after_s: Optional[float]) -> float:
        with self._rng_lock:
            return self.backoff.delay(retry_index, self._rng, retry_after_s)

    def random(self) -> float:
        with self._rng_lock:
            return self._rng.random()

    def purge_cache(self) -> None:
        if self.cache is not None:
            self.cache.purge()


_default_lock = threading.Lock()
_default_runtime: Optional[LlmRuntime] = None


def default_runtime() -> LlmRuntime:
    """The process runtime, built from the environment on first use."""
    global _default_runtime
    with _default_lock:
        if _default_runtime is None:
            _default_runtime = LlmRuntime(config=LlmConfig.from_env())
        return _default_runtime


def set_default_runtime(runtime: LlmRuntime) -> None:
    global _default_runtime
    with _default_lock:
        _default_runtime = runtime


def reset_default_runtime() -> None:
    """Drops the process runtime (breakers, cache); the next use rebuilds it from env."""
    global _default_runtime
    with _default_lock:
        _default_runtime = None


def purge_default_cache() -> None:
    """Empties the process response cache, if one exists (case erasure, ADR-010/024)."""
    with _default_lock:
        runtime = _default_runtime
    if runtime is not None:
        runtime.purge_cache()


def _outcome_for(exc: BaseException) -> str:
    if isinstance(exc, LlmCircuitOpen):
        return "circuit_open"
    if isinstance(exc, BudgetExceeded):
        return "budget_exceeded"
    if isinstance(exc, LlmTimeout):
        return "timeout"
    if isinstance(exc, LlmRateLimited):
        return "rate_limited"
    return "error"


def _parse_completion(body: Dict[str, Any]) -> Tuple[str, Optional[int], Optional[int], Optional[int]]:
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise LlmResponseError("response has no choices[0].message.content") from None
    if not isinstance(content, str):
        raise LlmResponseError("completion content is not text")
    usage = body.get("usage") if isinstance(body, dict) else None
    usage = usage if isinstance(usage, dict) else {}

    def _int(name):
        v = usage.get(name)
        return int(v) if isinstance(v, (int, float)) and v >= 0 else None

    return content, _int("prompt_tokens"), _int("completion_tokens"), _int("total_tokens")


class ResilientLlmClient:
    """Cheap to construct (per request); all shared state is in the runtime."""

    def __init__(self, api_key: str, model: str, runtime: Optional[LlmRuntime] = None):
        self.api_key = api_key or ""
        self.model = model
        self._runtime = runtime

    @property
    def runtime(self) -> LlmRuntime:
        return self._runtime or default_runtime()

    def complete(self, request: LlmRequest) -> LlmResponse:
        """Production call: cache (if enabled), fallback model (if configured), budget,
        one observer event, then an optional shadow run."""
        response = self._run(request, production=True)
        rt = self.runtime
        if rt.shadow is not None and not response.cache_hit:
            rt.shadow.submit(self.api_key, request, response)
        return response

    def complete_shadow(self, request: LlmRequest) -> LlmResponse:
        """Shadow call (ShadowRunner only): this model only — no cache, no fallback model,
        no budget, never triggers another shadow run. Still emits one observer event."""
        return self._run(request, production=False)

    # -- internals -------------------------------------------------------------------
    def _run(self, request: LlmRequest, production: bool) -> LlmResponse:
        if not KIND_RE.match(request.kind or ""):
            raise ValueError("LlmRequest.kind must match ^[a-z0-9_.]{1,64}$")
        rt = self.runtime
        started = rt.clock()
        state = {"retries": 0, "model": self.model}
        try:
            response = self._complete(rt, request, state, production)
        except Exception as exc:
            self._emit(rt, request, state["model"], _outcome_for(exc), started, None, None, False, state["retries"])
            raise
        outcome = "fallback" if response.used_fallback_model else "ok"
        self._emit(rt, request, response.model, outcome, started, response.prompt_tokens,
                   response.completion_tokens, response.cache_hit, response.retries)
        return response

    def _complete(self, rt: LlmRuntime, request: LlmRequest, state: Dict[str, Any], production: bool) -> LlmResponse:
        if not self.api_key:
            raise LlmNotConfigured("no API key configured")

        key = None
        if (production and rt.cache is not None
                and is_cache_eligible(request.system, request.prompt, request.temperature)):
            pv = request.prompt_version.label if request.prompt_version else ""
            key = cache_key(self.model, pv, request.system, request.prompt, request.temperature,
                            request.max_tokens, request.json_mode)
            hit = rt.cache.get(key)
            if hit is not None:  # spends no tokens, so the budget is neither checked nor charged
                return LlmResponse(text=hit, model=self.model, prompt_tokens=None,
                                   completion_tokens=None, cache_hit=True)

        budget = request.budget if production else None
        estimate = estimate_tokens(request.system, request.prompt, request.max_tokens)
        if budget is not None:
            budget.ensure_fits(estimate)

        models = [self.model]
        fallback = rt.config.fallback_for(self.model) if production else None
        if fallback:
            models.append(fallback)

        last_exc: Optional[BaseException] = None
        for model in models:
            state["model"] = model
            try:
                text, p_tok, c_tok, total = self._call_model(rt, model, request, state)
            except LlmError as exc:
                last_exc = exc
                if model != models[-1]:
                    logger.warning("LLM call on primary model failed (%s); trying the fallback model.",
                                   type(exc).__name__)
                continue
            if budget is not None:
                budget.charge(total if total is not None else estimate)
            used_fallback = model != self.model
            if key is not None and not used_fallback:
                rt.cache.put(key, text)
            return LlmResponse(text=text, model=model, prompt_tokens=p_tok, completion_tokens=c_tok,
                               cache_hit=False, retries=state["retries"], used_fallback_model=used_fallback)
        assert last_exc is not None
        raise last_exc

    def _call_model(self, rt: LlmRuntime, model: str, request: LlmRequest, state: Dict[str, Any]):
        breaker = rt.breaker(model)
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.prompt},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}
        timeout = request.timeout_s if request.timeout_s is not None else rt.config.timeout_s

        attempt = 0
        while True:
            if not breaker.allow():
                raise LlmCircuitOpen("circuit open for this model")
            try:
                try:
                    body = rt.transport(payload, self.api_key, timeout)
                    result = _parse_completion(body)
                except LlmError:
                    raise
                except Exception as raw:  # a custom transport's untyped failure
                    raise classify_transport_error(raw) from None
            except LlmError as exc:
                if counts_toward_breaker(exc):
                    breaker.record_failure()
                else:
                    breaker.record_success()  # the provider answered
                attempt += 1
                if not is_retryable(exc) or attempt >= rt.config.max_attempts:
                    raise
                if breaker.state == "open":
                    raise LlmCircuitOpen("circuit opened during retries") from None
                retry_after = exc.retry_after_s if isinstance(exc, LlmRateLimited) else None
                rt.sleep(rt.backoff_delay(attempt - 1, retry_after))
                state["retries"] += 1
                continue
            breaker.record_success()
            return result

    def _emit(self, rt, request, model, outcome, started, p_tok, c_tok, cache_hit, retries) -> None:
        try:
            event = LlmCallEvent(
                model=model, kind=request.kind, outcome=outcome,
                latency_s=max(0.0, rt.clock() - started), prompt_tokens=p_tok,
                completion_tokens=c_tok, cache_hit=cache_hit, retries=retries,
                circuit_state=rt.breaker(model).state,
            )
        except Exception:  # noqa: BLE001 — telemetry must never break the call
            logger.exception("Could not build LLM call event.")
            return
        emit_llm_event(event)
