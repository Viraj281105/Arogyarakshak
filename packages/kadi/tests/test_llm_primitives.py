"""Unit tests for the kadi.llm building blocks (WS2, ADR-024): config, retry classification,
backoff, circuit breaker, token budget, response cache and the observer event type.

Everything time-dependent uses an injected fake clock / seeded RNG — nothing sleeps.
"""

import dataclasses
import random
import socket
import urllib.error

import pytest

from kadi.llm.breaker import CircuitBreaker
from kadi.llm.budget import TokenBudget, estimate_tokens
from kadi.llm.cache import ResponseCache, cache_key, is_cache_eligible
from kadi.llm.config import DEPRECATED_GROQ_MODELS, LlmConfig
from kadi.llm.errors import (
    BudgetExceeded,
    LlmCircuitOpen,
    LlmClientError,
    LlmConnectionError,
    LlmRateLimited,
    LlmResponseError,
    LlmServerError,
    LlmTimeout,
)
from kadi.llm.observer import (
    CIRCUIT_STATES,
    OUTCOMES,
    LlmCallEvent,
    clear_llm_observers,
    emit_llm_event,
    register_llm_observer,
)
from kadi.llm.prompts import PromptVersion, get_prompt_version, register_prompt_version
from kadi.llm.retry import BackoffPolicy, counts_toward_breaker, is_retryable
from kadi.llm.transport import classify_transport_error


class FakeClock:
    def __init__(self, t: float = 1000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s


# ---- config ------------------------------------------------------------------------
def test_config_defaults_are_conservative():
    c = LlmConfig.from_env({})
    assert c.fallback_model == ""
    assert c.cache_enabled is False
    assert c.shadow_enabled is False
    assert c.case_token_budget == 0
    assert c.max_attempts >= 1


def test_config_reads_env_and_clamps_bad_values():
    c = LlmConfig.from_env({
        "GROQ_FALLBACK_MODEL": "qwen/qwen3.6-27b",
        "LLM_MAX_ATTEMPTS": "0",
        "LLM_BACKOFF_BASE_SECONDS": "not-a-number",
        "LLM_CACHE_ENABLED": "TRUE",
        "LLM_CACHE_MAX_ENTRIES": "10",
        "LLM_CASE_TOKEN_BUDGET": "5000",
        "LLM_SHADOW_SAMPLE_RATE": "7",
    })
    assert c.fallback_model == "qwen/qwen3.6-27b"
    assert c.max_attempts == 1  # clamped, never zero attempts
    assert c.backoff_base_s == LlmConfig().backoff_base_s  # invalid -> default
    assert c.cache_enabled is True and c.cache_max_entries == 10
    assert c.case_token_budget == 5000
    assert c.shadow_sample_rate == 1.0  # clamped to [0, 1]


@pytest.mark.parametrize("model", sorted(DEPRECATED_GROQ_MODELS))
def test_deprecated_fallback_and_shadow_models_are_refused(model):
    c = LlmConfig.from_env({"GROQ_FALLBACK_MODEL": model, "LLM_SHADOW_MODEL": model})
    assert c.fallback_model == ""
    assert c.shadow_model == ""


def test_fallback_model_equal_to_primary_is_not_used():
    c = LlmConfig(fallback_model="openai/gpt-oss-120b")
    assert c.fallback_for("openai/gpt-oss-120b") is None
    assert c.fallback_for("other/model") == "openai/gpt-oss-120b"
    assert LlmConfig().fallback_for("openai/gpt-oss-120b") is None


# ---- retry classification ------------------------------------------------------------
@pytest.mark.parametrize(
    "exc, retryable, breaker",
    [
        (LlmTimeout("t"), True, True),
        (LlmConnectionError("c"), True, True),
        (LlmRateLimited("r"), True, True),
        (LlmServerError("s", status=503), True, True),
        (LlmClientError("auth", status=401), False, False),
        (LlmClientError("bad", status=400), False, False),
        (LlmResponseError("malformed"), False, False),
        (BudgetExceeded("b"), False, False),
        (LlmCircuitOpen("o"), False, False),
        (ValueError("unexpected"), False, False),
    ],
)
def test_retry_and_breaker_classification(exc, retryable, breaker):
    assert is_retryable(exc) is retryable
    assert counts_toward_breaker(exc) is breaker


class _Headers(dict):
    def get(self, k, default=None):  # case-insensitive like http.client.HTTPMessage
        for key, v in self.items():
            if key.lower() == k.lower():
                return v
        return default


def _http_error(code, headers=None):
    return urllib.error.HTTPError("https://example.invalid", code, "x", _Headers(headers or {}), None)


def test_transport_error_classification():
    assert isinstance(classify_transport_error(socket.timeout("timed out")), LlmTimeout)
    assert isinstance(classify_transport_error(TimeoutError()), LlmTimeout)
    assert isinstance(classify_transport_error(urllib.error.URLError(socket.timeout())), LlmTimeout)
    assert isinstance(classify_transport_error(urllib.error.URLError("refused")), LlmConnectionError)
    rl = classify_transport_error(_http_error(429, {"Retry-After": "3"}))
    assert isinstance(rl, LlmRateLimited) and rl.retry_after_s == 3.0
    assert classify_transport_error(_http_error(429, {"Retry-After": "soon"})).retry_after_s is None
    assert isinstance(classify_transport_error(_http_error(500)), LlmServerError)
    assert isinstance(classify_transport_error(_http_error(408)), LlmServerError)
    e = classify_transport_error(_http_error(404))
    assert isinstance(e, LlmClientError) and e.status == 404


def test_transport_errors_never_carry_response_bodies():
    """An HTTPError body can echo the prompt; the classified error message must not."""
    err = classify_transport_error(_http_error(400))
    assert "x" not in str(err).split()  # only the status, not the reason/body text


# ---- backoff -------------------------------------------------------------------------
def test_backoff_schedule_with_seeded_jitter_is_bounded_and_reproducible():
    policy = BackoffPolicy(base_s=0.5, max_s=4.0)
    delays = [policy.delay(i, random.Random(7)) for i in range(6)]
    # Independent recomputation of the documented formula with the same seed.
    expected = []
    for i in range(6):
        cap = min(4.0, 0.5 * 2 ** i)
        expected.append(random.Random(7).uniform(cap / 2, cap))
    assert delays == expected
    for i, d in enumerate(delays):
        cap = min(4.0, 0.5 * 2 ** i)
        assert cap / 2 <= d <= cap
    assert max(delays) <= 4.0  # capped


def test_backoff_honours_retry_after_but_stays_capped():
    policy = BackoffPolicy(base_s=0.5, max_s=8.0)
    assert policy.delay(0, random.Random(1), retry_after_s=3.0) == 3.0
    assert policy.delay(0, random.Random(1), retry_after_s=60.0) == 8.0


# ---- circuit breaker -------------------------------------------------------------------
def test_breaker_opens_after_threshold_consecutive_failures():
    clock = FakeClock()
    b = CircuitBreaker(failure_threshold=3, recovery_s=30, clock=clock)
    assert b.state == "closed"
    for _ in range(2):
        assert b.allow()
        b.record_failure()
    assert b.state == "closed"
    b.record_success()  # a success resets the consecutive count
    for _ in range(3):
        assert b.allow()
        b.record_failure()
    assert b.state == "open"
    assert b.allow() is False


def test_breaker_half_open_admits_exactly_one_probe_and_closes_on_success():
    clock = FakeClock()
    b = CircuitBreaker(failure_threshold=1, recovery_s=30, clock=clock)
    b.record_failure()
    assert b.state == "open"
    clock.advance(29.9)
    assert b.allow() is False
    clock.advance(0.2)
    assert b.allow() is True  # the probe
    assert b.state == "half_open"
    assert b.allow() is False  # a second caller during the probe is rejected
    b.record_success()
    assert b.state == "closed"
    assert b.allow() is True


def test_breaker_failed_probe_reopens_and_restarts_the_timer():
    clock = FakeClock()
    b = CircuitBreaker(failure_threshold=1, recovery_s=10, clock=clock)
    b.record_failure()
    clock.advance(10)
    assert b.allow()
    b.record_failure()
    assert b.state == "open"
    clock.advance(9)
    assert b.allow() is False
    clock.advance(1)
    assert b.allow() is True


def test_breaker_is_safe_under_concurrent_use():
    import threading

    b = CircuitBreaker(failure_threshold=1000, recovery_s=1, clock=FakeClock())

    def hammer():
        for _ in range(200):
            b.allow()
            b.record_failure()

    threads = [threading.Thread(target=hammer) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert b.state == "open"  # 1600 failures >= threshold; no lost update kept it closed


# ---- token budget ------------------------------------------------------------------------
def test_estimate_is_conservative():
    assert estimate_tokens("abcd", "abcd", max_tokens=10) == 2 + 10
    assert estimate_tokens("", "a", max_tokens=0) == 1


def test_budget_enforcement():
    b = TokenBudget(limit=100)
    b.ensure_fits(100)
    b.charge(60)
    assert b.used == 60 and b.remaining == 40
    with pytest.raises(BudgetExceeded):
        b.ensure_fits(41)
    b.ensure_fits(40)


def test_zero_limit_means_unlimited():
    b = TokenBudget(limit=0)
    b.ensure_fits(10**9)
    b.charge(10**9)
    assert b.remaining is None


# ---- cache -----------------------------------------------------------------------------
_RAW = "Patient Name: Asha Kulkarni\nPhone: 9876543210\nConsultation: 500"


def test_cache_key_is_a_digest_and_contains_no_input_text():
    k = cache_key("m", "kadi.extraction@1", "SYSTEM TEXT", _RAW, 0.0, 1024, True)
    assert len(k) == 64 and all(c in "0123456789abcdef" for c in k)
    for fragment in ("Asha", "Kulkarni", "9876543210", "Consultation", "SYSTEM"):
        assert fragment not in k


def test_cache_key_varies_with_model_version_and_params():
    base = ("m", "p@1", "s", "Consultation: 500", 0.0, 1024, True)
    k0 = cache_key(*base)
    assert cache_key("m2", *base[1:]) != k0
    assert cache_key(base[0], "p@2", *base[2:]) != k0
    assert cache_key(*base[:5], 512, True) != k0
    assert cache_key(*base[:6], False) != k0
    assert cache_key(*base) == k0


def test_only_pii_free_deterministic_requests_are_cache_eligible():
    assert is_cache_eligible("sys", "Consultation: 500\nTotal: 500", temperature=0.0)
    assert not is_cache_eligible("sys", _RAW, temperature=0.0)  # redaction would change it
    assert not is_cache_eligible("sys", "Consultation: 500", temperature=0.3)


def test_cache_lru_bound_ttl_and_purge():
    clock = FakeClock()
    c = ResponseCache(max_entries=2, ttl_s=10, clock=clock)
    c.put("a" * 64, "A")
    c.put("b" * 64, "B")
    assert c.get("a" * 64) == "A"  # touch a -> b is least recently used
    c.put("c" * 64, "C")
    assert c.get("b" * 64) is None and len(c) == 2
    clock.advance(10.1)
    assert c.get("a" * 64) is None  # expired
    c.put("d" * 64, "D")
    c.purge()
    assert len(c) == 0


def test_cache_refuses_non_digest_keys():
    c = ResponseCache(max_entries=2, ttl_s=10, clock=FakeClock())
    with pytest.raises(ValueError):
        c.put("Patient Name: Asha", "x")


# ---- prompt versions --------------------------------------------------------------------
def test_prompt_version_from_template_changes_when_the_template_changes():
    a = PromptVersion.from_template("t.one", "template A")
    b = PromptVersion.from_template("t.one", "template B")
    assert a.version != b.version and a.label.startswith("t.one@")
    assert PromptVersion.from_template("t.one", "template A") == a


def test_prompt_registry_round_trip_and_conflict():
    pv = PromptVersion("test.registry", "3")
    register_prompt_version(pv)
    register_prompt_version(pv)  # idempotent
    assert get_prompt_version("test.registry") == pv
    with pytest.raises(ValueError):
        register_prompt_version(PromptVersion("test.registry", "4"))
    with pytest.raises(ValueError):
        PromptVersion("Bad Name With Spaces", "1")


# ---- observer --------------------------------------------------------------------------
def test_event_type_has_no_free_text_fields():
    """WS1<->WS2 interface: the only str fields are enumerated/configured labels."""
    str_fields = {f.name for f in dataclasses.fields(LlmCallEvent) if f.type in (str, "str")}
    assert str_fields == {"model", "kind", "outcome", "circuit_state"}
    names = [f.name for f in dataclasses.fields(LlmCallEvent)]
    assert names == [
        "model", "kind", "outcome", "latency_s", "prompt_tokens", "completion_tokens",
        "cache_hit", "retries", "circuit_state",
    ]


def test_event_rejects_unenumerated_labels():
    ok = dict(model="m", kind="kadi.extraction", outcome="ok", latency_s=0.1, prompt_tokens=None,
              completion_tokens=None, cache_hit=False, retries=0, circuit_state="closed")
    LlmCallEvent(**ok)
    assert set(OUTCOMES) == {"ok", "error", "timeout", "rate_limited", "circuit_open", "budget_exceeded", "fallback"}
    assert set(CIRCUIT_STATES) == {"closed", "open", "half_open"}
    for field, bad in (("outcome", "weird"), ("circuit_state", "x"), ("kind", "Patient Asha said hi")):
        with pytest.raises(ValueError):
            LlmCallEvent(**{**ok, field: bad})


def test_observers_receive_events_and_failures_are_isolated():
    clear_llm_observers()
    seen = []

    def broken(_e):
        raise RuntimeError("observer bug")

    unregister_broken = register_llm_observer(broken)
    unregister = register_llm_observer(seen.append)
    ev = LlmCallEvent(model="m", kind="k", outcome="ok", latency_s=0.0, prompt_tokens=1,
                      completion_tokens=2, cache_hit=False, retries=0, circuit_state="closed")
    emit_llm_event(ev)  # must not raise despite the broken observer
    assert seen == [ev]
    unregister()
    unregister_broken()
    emit_llm_event(ev)
    assert seen == [ev]
