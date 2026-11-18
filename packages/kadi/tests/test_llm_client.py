"""Behaviour of ResilientLlmClient (WS2, ADR-024) with an injected fake transport, fake
clock, recording sleep and seeded RNG. No network, no real sleeping."""

import random
import threading

import pytest

from kadi.llm import (
    LlmCallEvent,
    LlmConfig,
    LlmRequest,
    LlmRuntime,
    PromptVersion,
    ResilientLlmClient,
    TokenBudget,
    clear_llm_observers,
    default_runtime,
    purge_default_cache,
    register_llm_observer,
    reset_default_runtime,
    set_default_runtime,
)
from kadi.llm.errors import (
    BudgetExceeded,
    LlmCircuitOpen,
    LlmClientError,
    LlmNotConfigured,
    LlmRateLimited,
    LlmResponseError,
    LlmServerError,
    LlmTimeout,
)


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


def completion(text="ok", prompt_tokens=11, completion_tokens=7):
    body = {"choices": [{"message": {"content": text}}]}
    if prompt_tokens is not None:
        body["usage"] = {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                         "total_tokens": prompt_tokens + completion_tokens}
    return body


class FakeTransport:
    """Plays a script of results per call: an exception instance is raised, a dict is
    returned. A callable script entry is called with the payload."""

    def __init__(self, *script, default=None):
        self.script = list(script)
        self.default = default
        self.calls = []
        self._lock = threading.Lock()

    def __call__(self, payload, api_key, timeout_s):
        with self._lock:
            self.calls.append({"payload": payload, "api_key": api_key, "timeout_s": timeout_s})
            item = self.script.pop(0) if self.script else self.default
        if callable(item) and not isinstance(item, BaseException):
            item = item(payload)
        if isinstance(item, BaseException):
            raise item
        return item


class Harness:
    def __init__(self, transport, **cfg):
        self.clock = FakeClock()
        self.sleeps = []
        self.transport = transport
        self.config = LlmConfig(**cfg)
        self.runtime = LlmRuntime(
            config=self.config, transport=transport, clock=self.clock,
            sleep=self.sleeps.append, rng=random.Random(1234),
        )
        self.events = []
        clear_llm_observers()
        register_llm_observer(self.events.append)

    def client(self, model="primary/model", api_key="test-key"):
        return ResilientLlmClient(api_key=api_key, model=model, runtime=self.runtime)


def req(**kw):
    base = dict(system="You are a test agent.", prompt="Consultation: 500", kind="test.kind",
                temperature=0.0, max_tokens=64, json_mode=True)
    base.update(kw)
    return LlmRequest(**base)


@pytest.fixture(autouse=True)
def _isolate():
    clear_llm_observers()
    reset_default_runtime()
    yield
    clear_llm_observers()
    reset_default_runtime()


# ---- happy path ----------------------------------------------------------------------
def test_success_returns_text_usage_and_one_ok_event():
    h = Harness(FakeTransport(completion("hello", 11, 7)))
    resp = h.client().complete(req(timeout_s=10.0))
    assert resp.text == "hello"
    assert (resp.model, resp.prompt_tokens, resp.completion_tokens) == ("primary/model", 11, 7)
    assert resp.cache_hit is False and resp.retries == 0 and resp.used_fallback_model is False
    call = h.transport.calls[0]
    assert call["timeout_s"] == 10.0 and call["api_key"] == "test-key"
    assert call["payload"] == {
        "model": "primary/model",
        "messages": [{"role": "system", "content": "You are a test agent."},
                     {"role": "user", "content": "Consultation: 500"}],
        "temperature": 0.0,
        "max_tokens": 64,
        "response_format": {"type": "json_object"},
    }
    assert [e.outcome for e in h.events] == ["ok"]
    e = h.events[0]
    assert (e.model, e.kind, e.prompt_tokens, e.completion_tokens, e.circuit_state) == (
        "primary/model", "test.kind", 11, 7, "closed")


def test_prose_mode_sends_no_response_format_and_default_timeout_applies():
    h = Harness(FakeTransport(completion("letter")), timeout_s=12.0)
    h.client().complete(req(json_mode=False, temperature=0.3, max_tokens=2048))
    call = h.transport.calls[0]
    assert "response_format" not in call["payload"]
    assert call["timeout_s"] == 12.0


def test_missing_api_key_raises_without_network():
    h = Harness(FakeTransport(completion()))
    with pytest.raises(LlmNotConfigured):
        h.client(api_key="").complete(req())
    assert h.transport.calls == []
    assert [e.outcome for e in h.events] == ["error"]


def test_invalid_kind_is_rejected_before_any_call():
    h = Harness(FakeTransport(completion()))
    with pytest.raises(ValueError):
        h.client().complete(req(kind="Free text kind"))
    assert h.transport.calls == []


# ---- retries ----------------------------------------------------------------------------
def test_transient_error_is_retried_with_seeded_backoff():
    h = Harness(FakeTransport(LlmServerError("HTTP 503", status=503), completion("ok")),
                max_attempts=3, backoff_base_s=0.5, backoff_max_s=8.0)
    resp = h.client().complete(req())
    assert resp.text == "ok" and resp.retries == 1
    expected = random.Random(1234).uniform(0.25, 0.5)  # retry 0: cap = 0.5
    assert h.sleeps == [expected]
    assert h.events[0].outcome == "ok" and h.events[0].retries == 1


def test_retries_exhausted_raises_the_last_error_and_reports_timeout():
    h = Harness(FakeTransport(default=LlmTimeout("t")), max_attempts=3)
    with pytest.raises(LlmTimeout):
        h.client().complete(req())
    assert len(h.transport.calls) == 3
    assert len(h.sleeps) == 2
    assert h.events[-1].outcome == "timeout" and h.events[-1].retries == 2


def test_client_errors_are_not_retried_and_do_not_open_the_breaker():
    h = Harness(FakeTransport(default=LlmClientError("HTTP 401", status=401)),
                max_attempts=3, breaker_failure_threshold=1)
    for _ in range(3):
        with pytest.raises(LlmClientError):
            h.client().complete(req())
    assert len(h.transport.calls) == 3  # one attempt per call, never short-circuited
    assert h.sleeps == []
    assert h.runtime.breaker("primary/model").state == "closed"
    assert {e.outcome for e in h.events} == {"error"}


def test_malformed_completion_is_a_response_error_not_retried():
    h = Harness(FakeTransport(default={"choices": []}), max_attempts=3)
    with pytest.raises(LlmResponseError):
        h.client().complete(req())
    assert len(h.transport.calls) == 1


def test_rate_limit_honours_retry_after():
    h = Harness(FakeTransport(LlmRateLimited("HTTP 429", retry_after_s=2.0), completion()),
                max_attempts=2, backoff_base_s=0.5, backoff_max_s=8.0)
    h.client().complete(req())
    assert h.sleeps == [2.0]


def test_rate_limit_exhausted_reports_rate_limited():
    h = Harness(FakeTransport(default=LlmRateLimited("HTTP 429")), max_attempts=2)
    with pytest.raises(LlmRateLimited):
        h.client().complete(req())
    assert h.events[-1].outcome == "rate_limited"


# ---- circuit breaker ---------------------------------------------------------------------
def test_breaker_opens_and_then_short_circuits_without_network():
    h = Harness(FakeTransport(default=LlmServerError("HTTP 500", status=500)),
                max_attempts=1, breaker_failure_threshold=2, breaker_recovery_s=30)
    for _ in range(2):
        with pytest.raises(LlmServerError):
            h.client().complete(req())
    assert h.runtime.breaker("primary/model").state == "open"
    with pytest.raises(LlmCircuitOpen):
        h.client().complete(req())
    assert len(h.transport.calls) == 2  # the third call never reached the transport
    assert h.events[-1].outcome == "circuit_open" and h.events[-1].circuit_state == "open"

    # Recovery: after the timeout a single probe goes out and closes the breaker.
    h.clock.advance(30)
    h.transport.default = completion("recovered")
    assert h.client().complete(req()).text == "recovered"
    assert h.runtime.breaker("primary/model").state == "closed"


def test_retries_stop_as_soon_as_the_breaker_opens():
    h = Harness(FakeTransport(default=LlmTimeout("t")), max_attempts=5, breaker_failure_threshold=2)
    with pytest.raises(LlmCircuitOpen):
        h.client().complete(req())
    assert len(h.transport.calls) == 2


def test_breakers_are_shared_across_client_instances_in_the_runtime():
    h = Harness(FakeTransport(default=LlmServerError("HTTP 502", status=502)),
                max_attempts=1, breaker_failure_threshold=1)
    with pytest.raises(LlmServerError):
        h.client().complete(req())
    with pytest.raises(LlmCircuitOpen):
        h.client().complete(req())  # a NEW client instance sees the open breaker


# ---- fallback model -------------------------------------------------------------------------
def test_fallback_model_is_used_when_the_primary_fails():
    def by_model(payload):
        if payload["model"] == "primary/model":
            return LlmClientError("HTTP 404", status=404)
        return completion("from fallback")

    h = Harness(FakeTransport(default=by_model), fallback_model="fallback/model", max_attempts=1)
    resp = h.client().complete(req())
    assert resp.text == "from fallback" and resp.model == "fallback/model" and resp.used_fallback_model
    assert [c["payload"]["model"] for c in h.transport.calls] == ["primary/model", "fallback/model"]
    assert h.events[-1].outcome == "fallback" and h.events[-1].model == "fallback/model"


def test_open_primary_breaker_goes_straight_to_the_fallback():
    h = Harness(FakeTransport(LlmServerError("HTTP 500", status=500), completion("fb1"), completion("fb2")),
                fallback_model="fallback/model", max_attempts=1, breaker_failure_threshold=1)
    assert h.client().complete(req()).text == "fb1"
    assert h.client().complete(req()).text == "fb2"
    assert [c["payload"]["model"] for c in h.transport.calls] == [
        "primary/model", "fallback/model", "fallback/model"]


def test_no_fallback_configured_means_a_single_model():
    h = Harness(FakeTransport(default=LlmClientError("HTTP 404", status=404)), max_attempts=1)
    with pytest.raises(LlmClientError):
        h.client().complete(req())
    assert len(h.transport.calls) == 1


# ---- budget ---------------------------------------------------------------------------------
def test_budget_exceeded_raises_before_any_network_call():
    h = Harness(FakeTransport(default=completion()))
    budget = TokenBudget(limit=50)
    with pytest.raises(BudgetExceeded):
        h.client().complete(req(max_tokens=64, budget=budget))
    assert h.transport.calls == []
    assert h.events[-1].outcome == "budget_exceeded"


def test_budget_is_charged_with_actual_usage_across_calls():
    h = Harness(FakeTransport(default=completion("ok", 30, 20)))
    budget = TokenBudget(limit=200)
    h.client().complete(req(max_tokens=64, budget=budget))
    assert budget.used == 50
    h.client().complete(req(max_tokens=64, budget=budget))
    assert budget.used == 100
    with pytest.raises(BudgetExceeded):
        h.client().complete(req(max_tokens=100, budget=budget))  # 100 + estimate > 200


def test_budget_charges_the_estimate_when_usage_is_missing():
    h = Harness(FakeTransport(default=completion("ok", None)))
    budget = TokenBudget(limit=10_000)
    h.client().complete(req(system="abcd", prompt="abcd", max_tokens=10, budget=budget))
    assert budget.used == 12


# ---- cache ----------------------------------------------------------------------------------
def test_cache_is_off_by_default():
    h = Harness(FakeTransport(default=completion()))
    assert h.runtime.cache is None
    h.client().complete(req())
    h.client().complete(req())
    assert len(h.transport.calls) == 2


def test_enabled_cache_serves_identical_pii_free_requests():
    h = Harness(FakeTransport(default=completion("cached?")), cache_enabled=True)
    pv = PromptVersion("test.kind", "1")
    first = h.client().complete(req(prompt_version=pv))
    second = h.client().complete(req(prompt_version=pv))
    assert first.cache_hit is False and second.cache_hit is True and second.text == "cached?"
    assert len(h.transport.calls) == 1
    assert [e.cache_hit for e in h.events] == [False, True]
    # a different prompt version is a different key
    h.client().complete(req(prompt_version=PromptVersion("test.kind", "2")))
    assert len(h.transport.calls) == 2


def test_cache_never_stores_inputs_with_identifiers_or_nonzero_temperature():
    h = Harness(FakeTransport(default=completion()), cache_enabled=True)
    pii = "Patient Name: Asha Kulkarni\nConsultation: 500"
    h.client().complete(req(prompt=pii))
    h.client().complete(req(prompt=pii))
    h.client().complete(req(temperature=0.3))
    h.client().complete(req(temperature=0.3))
    assert len(h.transport.calls) == 4
    assert len(h.runtime.cache) == 0


def test_cache_keys_hold_no_raw_text_and_purge_empties_it():
    h = Harness(FakeTransport(default=completion()), cache_enabled=True)
    set_default_runtime(h.runtime)
    h.client().complete(req(prompt="Consultation: 500\nRoom Rent: 4000"))
    keys = h.runtime.cache.keys()
    assert len(keys) == 1
    for k in keys:
        assert len(k) == 64
        assert "Consultation" not in k and "500" not in k
    purge_default_cache()
    assert len(h.runtime.cache) == 0


def test_purge_default_cache_is_a_noop_when_disabled():
    set_default_runtime(LlmRuntime(config=LlmConfig()))
    purge_default_cache()  # must not raise


# ---- observer: no text, property-style ----------------------------------------------------------
def test_events_never_contain_prompt_or_response_text():
    rng = random.Random(99)
    alphabet = "abcdefghijklmnopqrstuvwxyzआरोग्य0123456789 "
    for i in range(40):
        secret_in = "IN" + "".join(rng.choice(alphabet) for _ in range(rng.randint(8, 40)))
        secret_out = "OUT" + "".join(rng.choice(alphabet) for _ in range(rng.randint(8, 40)))
        outcome_kind = i % 4
        if outcome_kind == 0:
            transport = FakeTransport(default=completion(secret_out))
        elif outcome_kind == 1:
            transport = FakeTransport(default=LlmClientError(secret_out, status=400))
        elif outcome_kind == 2:
            transport = FakeTransport(default=LlmTimeout(secret_out))
        else:
            transport = FakeTransport(default={"choices": [{"message": {"content": None}}], "x": secret_out})
        h = Harness(transport, max_attempts=2, cache_enabled=bool(i % 2))
        try:
            h.client().complete(req(system=secret_in, prompt=secret_in + " " + secret_in))
        except Exception:
            pass
        assert len(h.events) == 1
        rendered = repr(h.events[0]) + str(vars(h.events[0]))
        for secret in (secret_in, secret_out, secret_in[2:12], secret_out[3:13]):
            assert secret not in rendered


def test_every_event_is_an_llmcallevent_with_bounded_labels():
    h = Harness(FakeTransport(default=completion()))
    h.client().complete(req())
    assert all(isinstance(e, LlmCallEvent) for e in h.events)


# ---- threads --------------------------------------------------------------------------------
def test_concurrent_calls_from_the_threadpool_each_emit_one_event():
    h = Harness(FakeTransport(default=completion()))
    errors = []

    def worker():
        try:
            for _ in range(25):
                h.client().complete(req())
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert len(h.events) == 200 and len(h.transport.calls) == 200


# ---- default runtime -------------------------------------------------------------------------------
def test_default_runtime_reads_the_environment_lazily(monkeypatch):
    monkeypatch.setenv("LLM_CACHE_ENABLED", "true")
    monkeypatch.setenv("LLM_MAX_ATTEMPTS", "4")
    reset_default_runtime()
    rt = default_runtime()
    assert rt.config.cache_enabled is True and rt.config.max_attempts == 4
    assert default_runtime() is rt
