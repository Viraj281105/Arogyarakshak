"""WS1: Prometheus metrics - bounded labels, no PHI in labels, /metrics gating, middleware."""

import random
import re
import string

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.telemetry import llm_metrics
from app.telemetry import metrics as m
from app.telemetry.settings import TelemetrySettings
from tests.telemetry_helpers import PHI_SAMPLES, label_values


def _event(**kw):
    class Ev:
        model = "openai/gpt-oss-120b"
        kind = "extraction"
        outcome = "ok"
        latency_s = 0.5
        prompt_tokens = 100
        completion_tokens = 20
        cache_hit = False
        retries = 0
        circuit_state = "closed"

    ev = Ev()
    for k, v in kw.items():
        setattr(ev, k, v)
    return ev


@pytest.fixture(autouse=True)
def fresh_metrics():
    routes = m.get_known_routes()
    m.reset_for_tests()
    llm_metrics.reset_for_tests()
    yield
    m.set_known_routes(routes)
    m.reset_for_tests()
    llm_metrics.reset_for_tests()


def test_http_metrics_use_route_template_only():
    m.set_known_routes({"/api/v1/kadi/cases/{case_id}"})
    m.record_http_request("GET", "/api/v1/kadi/cases/{case_id}", 200, 0.02)
    text = m.render().decode()
    assert 'route="/api/v1/kadi/cases/{case_id}"' in text
    assert "arogya_http_requests_total" in text
    assert "arogya_http_request_duration_seconds_bucket" in text


def test_phi_never_reaches_any_label_http():
    for phi in PHI_SAMPLES:
        m.record_http_request(phi, phi, 200, 0.01)
        m.record_http_request("POST", phi, 413, 0.01)
        m.record_stage("ocr " + phi, 0.1)
        m.record_case_processing(1.0, phi)
        m.record_upload_rejection(phi, phi)
    text = m.render().decode()
    for phi in PHI_SAMPLES:
        assert phi not in text
    for value in label_values(text):
        assert not re.search(r"CASE-|Ramesh|@|diabetes|9876", value)


def test_phi_never_reaches_any_label_llm():
    for phi in PHI_SAMPLES:
        llm_metrics.record_llm_event(_event(model=phi, kind=phi, outcome=phi, circuit_state=phi))
    text = m.render().decode()
    for phi in PHI_SAMPLES:
        assert phi not in text


def test_random_fuzz_keeps_cardinality_bounded():
    rng = random.Random(7)
    alphabet = string.ascii_letters + string.digits + '/-_ {}"\\\n'
    for _ in range(3000):
        junk = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 40)))
        m.record_http_request(junk, "/" + junk, rng.choice([200, 404, 999, -5]), 0.01)
        m.record_stage(junk, 0.01)
        m.record_upload_rejection(junk, junk)
        llm_metrics.record_llm_event(_event(model=junk, kind=junk, outcome=junk, circuit_state=junk))
    text = m.render().decode()
    series = [ln for ln in text.splitlines() if ln and not ln.startswith("#")]
    assert len(series) < 1500, len(series)
    routes = {v for v in label_values(text) if v.startswith("/") or v.startswith("<")}
    assert routes <= {"<unmatched>"}


def test_known_route_set_is_accepted_and_unknown_collapses():
    m.set_known_routes({"/health", "/api/v1/kadi/cases/{case_id}"})
    m.record_http_request("GET", "/health", 200, 0.001)
    m.record_http_request("GET", "/evil/CASE-1", 200, 0.001)
    text = m.render().decode()
    assert 'route="/health"' in text
    assert "CASE-1" not in text
    assert 'route="<unmatched>"' in text


def test_status_clamped_and_method_clamped():
    m.record_http_request("BREW", "<unmatched>", 99999, 0.01)
    text = m.render().decode()
    assert 'method="OTHER"' in text
    assert 'status="other"' in text


def test_llm_event_updates_counters_and_gauge():
    llm_metrics.record_llm_event(_event())
    llm_metrics.record_llm_event(_event(outcome="timeout", retries=2, circuit_state="open", cache_hit=True))
    text = m.render().decode()
    assert 'arogya_llm_calls_total{kind="extraction",model="openai/gpt-oss-120b",outcome="ok"} 1.0' in text
    assert 'outcome="timeout"' in text
    assert 'arogya_llm_tokens_total{direction="prompt"' in text
    assert re.search(r'arogya_llm_circuit_state\{model="openai/gpt-oss-120b"\} 2.0', text)
    assert "arogya_llm_retries_total" in text
    assert "arogya_llm_cache_hits_total" in text


def test_llm_event_tolerates_missing_tokens_and_bad_values():
    llm_metrics.record_llm_event(_event(prompt_tokens=None, completion_tokens=None, latency_s=-1))
    llm_metrics.record_llm_event(object())  # never raises into the caller


def test_pool_gauges_collect_without_error(monkeypatch):
    monkeypatch.setattr(m, "_db_engine", None)  # restored afterwards: no leaking fake engine
    class Pool:
        def size(self):
            return 5

        def checkedout(self):
            return 2

        def overflow(self):
            return 0

    class Eng:
        class sync_engine:
            pool = Pool()

    m.register_db_pool(Eng)
    text = m.render().decode()
    assert "arogya_db_pool_checked_out 2.0" in text
    assert "arogya_db_pool_size 5.0" in text

    class Bare:
        class sync_engine:
            pool = object()

    m.register_db_pool(Bare)  # pools without counters (SQLite) simply report nothing
    m.render()


def test_stage_timer_records_even_on_error():
    with pytest.raises(ValueError):
        with m.stage_timer("ocr"):
            raise ValueError("x")
    assert 'arogya_pipeline_stage_duration_seconds_count{outcome="error",stage="ocr"} 1.0' in m.render().decode()


# --- endpoint / middleware ---------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_endpoint_serves_prometheus_text_and_counts_requests(monkeypatch):
    monkeypatch.setattr("app.main.telemetry_settings", TelemetrySettings(metrics_enabled=True))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.get("/health/live")
        await c.get("/api/v1/kadi/cases/CASE-deadbeefdeadbeef/nope")
        r = await c.get("/metrics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    body = r.text
    assert 'route="/health/live"' in body
    assert "CASE-deadbeef" not in body
    assert "# TYPE arogya_http_requests_total counter" in body
    assert 'route="/metrics"' not in body  # the scrape itself is not counted


@pytest.mark.asyncio
async def test_metrics_endpoint_is_404_when_disabled(monkeypatch):
    monkeypatch.setattr("app.main.telemetry_settings", TelemetrySettings(metrics_enabled=False))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/metrics")
    assert r.status_code == 404


def test_metrics_not_in_openapi():
    assert "/metrics" not in app.openapi()["paths"]


def test_upload_rejection_is_derived_from_response_status():
    m.record_upload_rejection_from_response("POST", "/api/v1/kadi/cases/{case_id}/upload", 415)
    m.record_upload_rejection_from_response("GET", "/api/v1/kadi/cases/{case_id}", 415)
    text = m.render().decode()
    assert 'reason="unsupported_type"' in text
    assert text.count("arogya_upload_rejections_total{") == 1


def test_case_processing_histogram_has_10s_bucket_for_the_slo():
    m.record_case_processing(3.0, "completed")
    assert 'arogya_case_processing_seconds_bucket{le="10.0",outcome="completed"} 1.0' in m.render().decode()


def test_latency_tracker_feeds_prometheus_and_keeps_working():
    from app.latency_metrics import tracker

    tracker.reset()
    tracker.record("CASE-aaaaaaaaaaaaaaaa", 2.5, "completed")
    assert tracker.summary().sample_count == 1
    text = m.render().decode()
    assert 'arogya_case_processing_seconds_count{outcome="completed"} 1.0' in text
    assert "CASE-aaaa" not in text
    tracker.reset()
