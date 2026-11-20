"""WS2 -> WS1 glue: the app registers the Prometheus recorder as an LLM-client observer."""

import os
import subprocess
import sys

import pytest
from kadi.llm.observer import LlmCallEvent, emit_llm_event, register_llm_observer

import app.main  # noqa: F401
from app.telemetry import llm_metrics, metrics as telemetry_metrics


@pytest.fixture(autouse=True)
def _recorder_registered():
    """Other tests call ``clear_llm_observers()``, which wipes the registration that
    ``app.main`` makes once at import. Re-register (idempotent) so these tests do not
    depend on test order; the import-time registration itself is checked in a fresh
    process by ``test_importing_the_app_registers_the_recorder``."""
    unregister = register_llm_observer(llm_metrics.record_llm_event)
    yield
    unregister()


def test_importing_the_app_registers_the_recorder():
    code = (
        "import app.main\n"
        "from kadi.llm import observer\n"
        "from app.telemetry.llm_metrics import record_llm_event\n"
        "print(record_llm_event in observer._observers)"
    )
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(p for p in sys.path if p)}
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, check=True)
    assert out.stdout.strip().splitlines()[-1] == "True"


def test_resilient_client_events_reach_prometheus_llm_metrics():
    llm_metrics.reset_for_tests()
    emit_llm_event(
        LlmCallEvent(
            model="openai/gpt-oss-120b",
            kind="extraction",
            outcome="ok",
            latency_s=0.25,
            prompt_tokens=100,
            completion_tokens=20,
            cache_hit=False,
            retries=1,
            circuit_state="closed",
        )
    )
    text = telemetry_metrics.render().decode() if isinstance(telemetry_metrics.render(), bytes) else telemetry_metrics.render()
    assert 'arogya_llm_calls_total{kind="extraction",model="openai/gpt-oss-120b",outcome="ok"} 1.0' in text
    assert 'arogya_llm_tokens_total{direction="prompt"' in text
    assert "arogya_llm_retries_total" in text


def test_event_labels_carry_no_text_from_a_hostile_event():
    llm_metrics.reset_for_tests()
    emit_llm_event(
        LlmCallEvent(
            model="patient John Doe", kind="extraction", outcome="error", latency_s=0.1,
            prompt_tokens=None, completion_tokens=None, cache_hit=False, retries=0, circuit_state="open",
        )
    )
    text = telemetry_metrics.render().decode() if isinstance(telemetry_metrics.render(), bytes) else telemetry_metrics.render()
    assert "John" not in text and "Doe" not in text
