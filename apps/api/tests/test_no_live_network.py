"""Tests never reach the network (AGENTS.md network rule; WS2 review).

conftest.py clears GROQ_API_KEY (settings and environment) for every test and replaces
``urllib.request.urlopen`` — the only outbound HTTP path the API uses for Groq — with a guard
that records the attempt and raises. A test that needs a live-looking client sets a key and
patches the transport itself."""

import os
import urllib.request

import pytest

from app.config import settings
from app.main import app
from app.services.billnyay_llm import GroqClient, GroqClientFallback
from kadi.llm import LlmConfig, LlmRuntime, set_default_runtime
from tests.auth_test_client import AuthAwareTestClient

client = AuthAwareTestClient(app)

DENIAL_DOC = (
    b"Lifeline Multispeciality Hospital\n"
    b"Claim Rejection Letter\n"
    b"Denial Code: DEN-4471\n"
    b"Reason: Hospitalisation deemed for investigation only.\n"
    b"Total Amount: 20150\n"
)


def test_no_groq_key_is_visible_to_tests():
    assert settings.groq_api_key == ""
    assert "GROQ_API_KEY" not in os.environ


def test_urlopen_is_guarded(network_guard):
    with pytest.raises(RuntimeError, match="live network calls are forbidden in tests"):
        urllib.request.urlopen("https://api.groq.com/openai/v1/chat/completions", timeout=1)
    assert network_guard == ["https://api.groq.com/openai/v1/chat/completions"]


def test_unpatched_appeal_draft_makes_no_network_call(network_guard):
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    assert client.post(
        f"/api/v1/kadi/cases/{case_id}/upload", files={"file": ("denial.txt", DENIAL_DOC)}
    ).status_code == 202
    res = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal")
    assert res.status_code == 200
    assert res.json()["llm_backed"] is False
    assert network_guard == []


def test_a_keyed_client_without_a_patched_transport_is_stopped_by_the_guard(network_guard):
    set_default_runtime(LlmRuntime(config=LlmConfig(max_attempts=1)))
    c = GroqClient(api_key="not-a-real-key", model="m")
    out = c.generate("p", system="You are the Auditor Agent for BillNyay.")
    assert c.used_fallback is True
    assert out == GroqClientFallback().generate("p", system="You are the Auditor Agent for BillNyay.")
    assert network_guard == ["https://api.groq.com/openai/v1/chat/completions"]
