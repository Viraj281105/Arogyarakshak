"""kadi.extraction on the resilient client (WS2): same request, same parsing, and the same
heuristic fallback whenever the client fails — including the new failure modes (open
circuit, exhausted retries)."""

import json
import random

import pytest

from kadi.extraction import extract_entities_from_text, run_heuristic_extraction_fallback
from kadi.llm import (
    LlmConfig,
    LlmRuntime,
    clear_llm_observers,
    register_llm_observer,
    reset_default_runtime,
    set_default_runtime,
)
from kadi.llm.errors import LlmServerError, LlmTimeout

BILL = "Lifeline Hospital\nConsultation: 500\nX-Ray Chest: 700\nTotal Amount: 1200\n"


class Transport:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def __call__(self, payload, api_key, timeout_s):
        self.calls.append({"payload": payload, "timeout_s": timeout_s, "api_key": api_key})
        if isinstance(self.result, BaseException):
            raise self.result
        return {"choices": [{"message": {"content": self.result}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}}


def install(transport, **cfg):
    rt = LlmRuntime(config=LlmConfig(**cfg), transport=transport, sleep=lambda s: None, rng=random.Random(0))
    set_default_runtime(rt)
    return rt


@pytest.fixture(autouse=True)
def _isolate():
    reset_default_runtime()
    clear_llm_observers()
    yield
    reset_default_runtime()
    clear_llm_observers()


def test_extraction_goes_through_the_resilient_client():
    t = Transport(json.dumps({"hospital_name": "Lifeline Hospital", "total_amount": 1200.0}))
    install(t)
    events = []
    register_llm_observer(events.append)

    result = extract_entities_from_text(BILL, api_key="k", model="chosen/model")

    assert result.hospital_name == "Lifeline Hospital" and result.total_amount == 1200.0
    call = t.calls[0]
    assert call["timeout_s"] == 10  # unchanged per-call timeout
    assert call["payload"]["model"] == "chosen/model"
    assert call["payload"]["response_format"] == {"type": "json_object"}
    assert call["payload"]["temperature"] == 0.0 and call["payload"]["max_tokens"] == 1024
    assert [(e.kind, e.outcome) for e in events] == [("kadi.extraction", "ok")]


def test_model_defaults_to_groq_model_env(monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", "env/model")
    t = Transport(json.dumps({"total_amount": 1200.0}))
    install(t)
    extract_entities_from_text(BILL, api_key="k")
    assert t.calls[0]["payload"]["model"] == "env/model"


@pytest.mark.parametrize("failure", [LlmServerError("HTTP 503", status=503), LlmTimeout("t")])
def test_client_failure_falls_back_to_the_heuristic_extractor(failure):
    install(Transport(failure), max_attempts=2)
    assert extract_entities_from_text(BILL, api_key="k", model="m") == run_heuristic_extraction_fallback(BILL)


def test_open_circuit_falls_back_without_a_network_call():
    t = Transport(LlmServerError("HTTP 500", status=500))
    install(t, max_attempts=1, breaker_failure_threshold=1)
    extract_entities_from_text(BILL, api_key="k", model="m")
    assert len(t.calls) == 1
    assert extract_entities_from_text(BILL, api_key="k", model="m") == run_heuristic_extraction_fallback(BILL)
    assert len(t.calls) == 1  # short-circuited


def test_non_json_content_still_falls_back():
    install(Transport("not json at all"))
    assert extract_entities_from_text(BILL, api_key="k", model="m") == run_heuristic_extraction_fallback(BILL)


def test_no_key_never_touches_the_client(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    t = Transport("{}")
    install(t)
    assert extract_entities_from_text(BILL, api_key="") == run_heuristic_extraction_fallback(BILL)
    assert t.calls == []
