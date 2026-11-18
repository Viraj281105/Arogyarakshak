"""WS2 review fixes (ADR-024): overall deadline, effective per-attempt timeout, Retry-After
HTTP-date + separate clamp, guarded shadow submission, breaker generation guard, idempotent
observer registration. Fake clock + clock-advancing sleep/transport; nothing really sleeps."""

import random
import urllib.error
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import pytest

from kadi.llm import (
    LlmConfig,
    LlmRequest,
    LlmRuntime,
    ResilientLlmClient,
    clear_llm_observers,
    register_llm_observer,
)
from kadi.llm.breaker import CircuitBreaker
from kadi.llm.errors import LlmClientError, LlmRateLimited, LlmTimeout
from kadi.llm.observer import LlmCallEvent, emit_llm_event
from kadi.llm.retry import BackoffPolicy
from kadi.llm.transport import classify_transport_error


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class Rig:
    """Transport + sleep that advance a shared fake clock: a timeout costs the full
    per-attempt timeout it was given, a sleep costs its duration."""

    def __init__(self, script_by_model, **cfg):
        self.clock = Clock()
        self.calls = []
        self.sleeps = []
        self.script_by_model = script_by_model
        self.runtime = LlmRuntime(config=LlmConfig(**cfg), transport=self.transport, clock=self.clock,
                                  sleep=self.sleep, rng=random.Random(5))

    def sleep(self, s):
        self.sleeps.append(s)
        self.clock.t += s

    def transport(self, payload, api_key, timeout_s):
        model = payload["model"]
        self.calls.append((model, timeout_s, self.clock.t))
        result = self.script_by_model[model]
        if isinstance(result, LlmTimeout):
            self.clock.t += timeout_s
            raise result
        if isinstance(result, BaseException):
            raise result
        return {"choices": [{"message": {"content": result}}]}

    def complete(self, timeout_s=10.0, model="primary/model"):
        req = LlmRequest(system="s", prompt="Consultation: 500", kind="test.kind", timeout_s=timeout_s)
        return ResilientLlmClient("k", model, runtime=self.runtime).complete(req)


@pytest.fixture(autouse=True)
def _observers():
    clear_llm_observers()
    yield
    clear_llm_observers()


# ---- 1. overall deadline ------------------------------------------------------------------
def test_deadline_stops_retries_and_caps_the_last_attempt_timeout():
    rig = Rig({"primary/model": LlmTimeout("t")}, max_attempts=5, total_deadline_s=20.0,
              backoff_base_s=1.0, backoff_max_s=8.0)
    with pytest.raises(LlmTimeout):
        rig.complete(timeout_s=10.0)
    timeouts = [t for _, t, _ in rig.calls]
    assert len(rig.calls) == 2  # not 5: the deadline ran out
    assert timeouts[0] == 10.0
    assert timeouts[1] == pytest.approx(20.0 - rig.calls[1][2])  # capped to the remaining time
    assert timeouts[1] < 10.0
    assert rig.clock.t <= 20.0 + 1e-9


def test_never_sleeps_past_the_deadline():
    rig = Rig({"primary/model": LlmRateLimited("HTTP 429", retry_after_s=25.0)},
              max_attempts=5, total_deadline_s=20.0)
    with pytest.raises(LlmRateLimited):
        rig.complete()
    assert rig.sleeps == []  # a 25 s wait cannot fit in a 20 s deadline
    assert len(rig.calls) == 1


def test_fallback_model_is_not_tried_when_no_time_remains():
    rig = Rig({"primary/model": LlmTimeout("t"), "fallback/model": "fb"},
              max_attempts=1, total_deadline_s=20.0, fallback_model="fallback/model")
    with pytest.raises(LlmTimeout):
        rig.complete(timeout_s=20.0)
    assert [m for m, _, _ in rig.calls] == ["primary/model"]


def test_fallback_model_gets_only_the_remaining_time():
    rig = Rig({"primary/model": LlmTimeout("t"), "fallback/model": "fb"},
              max_attempts=1, total_deadline_s=20.0, fallback_model="fallback/model")
    assert rig.complete(timeout_s=12.0).text == "fb"
    assert rig.calls[1][0] == "fallback/model" and rig.calls[1][1] == pytest.approx(8.0)


def test_deadline_setting_is_validated_positive():
    default = LlmConfig().total_deadline_s
    assert default == 20.0
    for bad in ("0", "-5", "soon"):
        assert LlmConfig.from_env({"LLM_TOTAL_DEADLINE_SECONDS": bad}).total_deadline_s == default
    assert LlmConfig.from_env({"LLM_TOTAL_DEADLINE_SECONDS": "45"}).total_deadline_s == 45.0


# ---- 2. effective per-attempt timeout ------------------------------------------------------------
def test_llm_timeout_seconds_unset_means_the_call_site_timeout_applies():
    assert LlmConfig.from_env({}).timeout_s is None
    rig = Rig({"primary/model": "ok"})
    rig.complete(timeout_s=12.0)
    assert rig.calls[0][1] == 12.0


def test_llm_timeout_seconds_lowers_but_never_raises_the_call_site_timeout():
    rig = Rig({"primary/model": "ok"}, timeout_s=5.0)
    rig.complete(timeout_s=12.0)
    assert rig.calls[0][1] == 5.0
    rig2 = Rig({"primary/model": "ok"}, timeout_s=30.0)
    rig2.complete(timeout_s=10.0)
    assert rig2.calls[0][1] == 10.0


# ---- m3. Retry-After -----------------------------------------------------------------------------
class _Headers(dict):
    def get(self, k, default=None):
        for key, v in self.items():
            if key.lower() == k.lower():
                return v
        return default


def _429(value):
    return urllib.error.HTTPError("https://example.invalid", 429, "x", _Headers({"Retry-After": value}), None)


def test_retry_after_http_date_is_parsed():
    now = datetime(2026, 11, 18, 12, 0, 0, tzinfo=timezone.utc)
    err = classify_transport_error(_429(format_datetime(now + timedelta(seconds=7), usegmt=True)), now=now)
    assert err.retry_after_s == pytest.approx(7.0)
    past = classify_transport_error(_429(format_datetime(now - timedelta(seconds=30), usegmt=True)), now=now)
    assert past.retry_after_s == 0.0
    assert classify_transport_error(_429("not a date"), now=now).retry_after_s is None


def test_retry_after_has_its_own_clamp_above_the_backoff_cap():
    policy = BackoffPolicy(base_s=0.5, max_s=8.0, retry_after_max_s=30.0)
    assert policy.delay(0, random.Random(1), retry_after_s=12.0) == 12.0  # above max_s, allowed
    assert policy.delay(0, random.Random(1), retry_after_s=90.0) == 30.0  # clamped
    assert LlmConfig.from_env({"LLM_RETRY_AFTER_MAX_SECONDS": "15"}).retry_after_max_s == 15.0
    assert LlmConfig().retry_after_max_s == 30.0


# ---- m1. shadow submission can never discard a good response ---------------------------------------
def test_a_failing_shadow_submit_does_not_lose_the_production_response():
    rig = Rig({"primary/model": "good", "cand/model": "x"}, shadow_enabled=True, shadow_model="cand/model")

    def boom(*a, **k):
        raise RuntimeError("shadow bug")

    rig.runtime.shadow.submit = boom
    assert rig.complete().text == "good"


# ---- m2. breaker generation guard -------------------------------------------------------------------
def test_late_success_from_before_the_trip_does_not_close_an_open_breaker():
    clock = Clock()
    b = CircuitBreaker(failure_threshold=1, recovery_s=30, clock=clock)
    old = b.acquire()  # call A starts while closed
    other = b.acquire()  # call B starts while closed
    b.record_failure(other)  # B fails -> trip
    assert b.state == "open"
    b.record_success(old)  # A's late success belongs to the old generation
    assert b.state == "open"
    assert b.acquire() is None


def test_late_failure_does_not_clear_the_half_open_probe():
    clock = Clock()
    b = CircuitBreaker(failure_threshold=1, recovery_s=30, clock=clock)
    old = b.acquire()
    b.record_failure(b.acquire())  # trip
    clock.t += 30
    probe = b.acquire()
    assert probe is not None and b.state == "half_open"
    b.record_failure(old)  # late result from before the trip: ignored
    assert b.state == "half_open"
    assert b.acquire() is None  # the real probe is still in flight
    b.record_success(probe)
    assert b.state == "closed"


def test_allow_and_untokened_records_keep_working():
    b = CircuitBreaker(failure_threshold=1, recovery_s=30, clock=Clock())
    assert b.allow() is True
    b.record_failure()
    assert b.state == "open"


# ---- m6. idempotent observer registration -------------------------------------------------------------
def test_registering_the_same_observer_twice_delivers_once():
    seen = []
    unregister = register_llm_observer(seen.append)
    unregister_again = register_llm_observer(seen.append)
    ev = LlmCallEvent(model="m", kind="k", outcome="ok", latency_s=0.0, prompt_tokens=None,
                      completion_tokens=None, cache_hit=False, retries=0, circuit_state="closed")
    emit_llm_event(ev)
    assert seen == [ev]
    unregister()
    unregister_again()  # harmless
    emit_llm_event(ev)
    assert seen == [ev]


def test_client_error_on_primary_still_reaches_the_fallback_within_the_deadline():
    rig = Rig({"primary/model": LlmClientError("HTTP 404", status=404), "fallback/model": "fb"},
              fallback_model="fallback/model")
    assert rig.complete().text == "fb"
