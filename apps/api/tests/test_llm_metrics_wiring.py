"""WS2 -> WS1 glue: the app registers the Prometheus recorder as an LLM-client observer."""

from kadi.llm.observer import LlmCallEvent, emit_llm_event

import app.main  # noqa: F401  (importing the app performs the registration)
from app.telemetry import llm_metrics, metrics as telemetry_metrics


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
