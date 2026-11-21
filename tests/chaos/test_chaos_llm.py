"""Chaos: the LLM provider times out, errors, or the circuit opens.

Extraction must fall back to the offline heuristic (the document still processes), the
transport must not be hammered once the circuit is open, the API key must never reach a
response, and nothing here may touch the network (the transport is a stub).
"""

import random

import pytest
from kadi.llm import LlmConfig, LlmRuntime, set_default_runtime
from kadi.llm.errors import LlmServerError, LlmTimeout

from app.config import settings
from chaos_harness import TEXT_BILL, assert_no_leak, jobs, new_case, stream_events, upload
from chaos_harness import *  # noqa: F401,F403

API_KEY = "gsk_CHAOS_SECRET_KEY_0000"


class Transport:
    def __init__(self, error):
        self.error = error
        self.calls = 0

    def __call__(self, payload, api_key, timeout_s):
        self.calls += 1
        raise self.error


def install(transport, **cfg):
    cfg.setdefault("max_attempts", 1)
    runtime = LlmRuntime(config=LlmConfig(**cfg), transport=transport, sleep=lambda s: None, rng=random.Random(0))
    set_default_runtime(runtime)
    return runtime


@pytest.fixture
def groq_configured(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", API_KEY)


@pytest.mark.parametrize("error", [LlmTimeout("deadline"), LlmServerError("boom", 503), TimeoutError("socket"), ConnectionResetError("reset")])
def test_llm_failure_falls_back_and_the_document_still_completes(groq_configured, error):
    transport = Transport(error)
    install(transport)
    case_id = new_case()
    assert upload(case_id).status_code == 202
    assert transport.calls >= 1, "the live path was really exercised"
    events = stream_events(case_id)
    assert events[-1]["status"] == "completed"
    assert [state for state, _ in jobs(case_id)] == ["completed"]
    assert_no_leak(str(events), API_KEY)


def test_an_open_circuit_stops_calling_the_provider(groq_configured):
    transport = Transport(LlmServerError("down", 503))
    runtime = install(transport, breaker_failure_threshold=1, breaker_recovery_s=3600)
    first = new_case()
    assert upload(first).status_code == 202
    calls_after_first = transport.calls
    assert calls_after_first == 1
    assert runtime.breaker(settings.groq_model).state == "open"

    second = new_case()
    assert upload(second, TEXT_BILL + b"Dressing 100\n").status_code == 202
    assert transport.calls == calls_after_first, "an open circuit must not reach the transport"
    assert stream_events(second)[-1]["status"] == "completed"
    assert [state for state, _ in jobs(second)] == ["completed"]


def test_the_api_key_is_never_in_a_response_or_a_log(groq_configured, caplog):
    install(Transport(LlmServerError(f"upstream rejected key {API_KEY}", 401)))
    case_id = new_case()
    res = upload(case_id)
    assert API_KEY not in res.text
    assert API_KEY not in str(stream_events(case_id))
    # Logs name the exception type only (kadi.extraction): the provider message is not logged.
    assert API_KEY not in caplog.text


def test_no_live_network_is_attempted_when_the_provider_fails(groq_configured, network_guard):
    install(Transport(LlmTimeout("deadline")))
    upload(new_case())
    assert network_guard == [], "the stub transport replaced urllib; nothing reached the network"


def test_llm_outage_in_the_appeal_draft_path_degrades_instead_of_erroring(groq_configured):
    """BillNyay's GroqClient shares the runtime; a dead provider lands on its canned fallback."""
    from app.services.billnyay_llm import GroqClient

    install(Transport(LlmTimeout("deadline")))
    client = GroqClient(api_key=API_KEY, model=settings.groq_model)
    text = client.generate("draft something")
    assert client.used_fallback is True
    assert text and API_KEY not in text
