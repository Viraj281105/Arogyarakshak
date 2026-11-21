"""BillNyay's GroqClient on the resilient client (WS2, ADR-024).

Public behaviour is unchanged: same request shape and timeout, the same canned per-agent
offline fallback (``GroqClientFallback``) whenever the live call fails, ``used_fallback``
set in that case, and ``llm_client()`` still returns the fallback when no key is set. New:
an open circuit or an exhausted per-case token budget also lands on that fallback."""

import random

import pytest

from app.services import billnyay_llm
from app.services.billnyay_llm import GroqClient, GroqClientFallback, llm_client
from kadi.llm import (
    LlmConfig,
    LlmRuntime,
    TokenBudget,
    clear_llm_observers,
    register_llm_observer,
    set_default_runtime,
)
from kadi.llm.errors import LlmClientError, LlmServerError

AUDITOR_SYS = "You are the Auditor Agent for BillNyay.\nExtract the denial."
BARRISTER_SYS = "You are the Barrister Agent in BillNyay — a legal counsel."
CLINICIAN_SYS = "You are the Clinician Agent in BillNyay.\nCite evidence."


class Transport:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def __call__(self, payload, api_key, timeout_s):
        self.calls.append({"payload": payload, "timeout_s": timeout_s})
        if isinstance(self.result, BaseException):
            raise self.result
        return {"choices": [{"message": {"content": self.result}}],
                "usage": {"prompt_tokens": 40, "completion_tokens": 10, "total_tokens": 50}}


def install(transport, **cfg):
    rt = LlmRuntime(config=LlmConfig(**cfg), transport=transport, sleep=lambda s: None, rng=random.Random(0))
    set_default_runtime(rt)
    return rt


@pytest.fixture(autouse=True)
def _observers():
    clear_llm_observers()
    yield
    clear_llm_observers()


def test_live_call_keeps_the_request_shape_and_timeout():
    t = Transport('{"denial_code": "X"}')
    install(t)
    client = GroqClient(api_key="k", model="chosen/model")
    assert client.generate("prompt text") == '{"denial_code": "X"}'
    assert client.used_fallback is False
    call = t.calls[0]
    assert call["timeout_s"] == 12
    assert call["payload"] == {
        "model": "chosen/model",
        "messages": [{"role": "system", "content": "You are an expert healthcare auditor."},
                     {"role": "user", "content": "prompt text"}],
        "temperature": 0.0,
        "max_tokens": 1024,
        "response_format": {"type": "json_object"},
    }


def test_prose_mode_and_kwargs_pass_through():
    t = Transport("A long appeal letter. " * 10)
    install(t)
    GroqClient(api_key="k", model="m").generate(
        "p", system=BARRISTER_SYS, temperature=0.3, max_tokens=2048, json_mode=False, language="hi")
    payload = t.calls[0]["payload"]
    assert "response_format" not in payload
    assert payload["temperature"] == 0.3 and payload["max_tokens"] == 2048


@pytest.mark.parametrize("system, kind", [
    (AUDITOR_SYS, "billnyay.auditor"),
    (CLINICIAN_SYS, "billnyay.clinician"),
    (BARRISTER_SYS, "billnyay.barrister"),
    ("", "billnyay.generic"),
])
def test_each_agent_call_is_labelled_with_a_bounded_kind(system, kind):
    install(Transport("{}"))
    events = []
    register_llm_observer(events.append)
    GroqClient(api_key="k", model="m").generate("p", system=system)
    assert [e.kind for e in events] == [kind]


@pytest.mark.parametrize("system, json_mode, language", [
    (AUDITOR_SYS, True, "en"),
    (CLINICIAN_SYS, True, "en"),
    (BARRISTER_SYS, False, "hi"),
    (BARRISTER_SYS, False, "mr"),
])
def test_live_failure_returns_the_same_canned_fallback(system, json_mode, language):
    install(Transport(LlmServerError("HTTP 503", status=503)), max_attempts=2)
    client = GroqClient(api_key="k", model="m")
    out = client.generate("p", system=system, json_mode=json_mode, language=language)
    assert out == GroqClientFallback().generate("p", system=system, json_mode=json_mode, language=language)
    assert client.used_fallback is True


def test_open_circuit_returns_the_fallback_without_a_network_call():
    t = Transport(LlmServerError("HTTP 500", status=500))
    install(t, max_attempts=1, breaker_failure_threshold=1)
    GroqClient(api_key="k", model="m").generate("p", system=AUDITOR_SYS)
    client = GroqClient(api_key="k", model="m")
    out = client.generate("p", system=AUDITOR_SYS)
    assert len(t.calls) == 1
    assert client.used_fallback is True
    assert out == GroqClientFallback().generate("p", system=AUDITOR_SYS)


def test_auth_error_falls_back_once_without_retrying():
    t = Transport(LlmClientError("HTTP 401", status=401))
    install(t, max_attempts=3)
    client = GroqClient(api_key="k", model="m")
    client.generate("p", system=AUDITOR_SYS)
    assert len(t.calls) == 1 and client.used_fallback is True


def test_exhausted_token_budget_falls_back_without_a_network_call():
    t = Transport("{}")
    install(t)
    client = GroqClient(api_key="k", model="m", token_budget=TokenBudget(limit=60))
    client.generate("p", system=AUDITOR_SYS, max_tokens=16)  # fits; charged 50 actual tokens
    assert client.used_fallback is False
    client.generate("p", system=AUDITOR_SYS, max_tokens=16)  # 50 + estimate > 60
    assert client.used_fallback is True
    assert len(t.calls) == 1


def test_llm_client_without_a_key_is_the_offline_fallback(monkeypatch):
    monkeypatch.setattr(billnyay_llm.settings, "groq_api_key", "")
    assert isinstance(llm_client(), GroqClientFallback)


def test_llm_client_gives_each_pipeline_run_its_own_budget(monkeypatch):
    monkeypatch.setattr(billnyay_llm.settings, "groq_api_key", "k")
    install(Transport("{}"), case_token_budget=5000)
    a, b = llm_client(), llm_client()
    assert isinstance(a, GroqClient)
    assert a.token_budget is not b.token_budget
    assert a.token_budget.limit == 5000


def test_llm_client_budget_is_unlimited_by_default(monkeypatch):
    monkeypatch.setattr(billnyay_llm.settings, "groq_api_key", "k")
    install(Transport("{}"))
    assert llm_client().token_budget is None
