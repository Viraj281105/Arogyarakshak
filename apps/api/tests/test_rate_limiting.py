"""Regression tests for the per-client-IP rate limiter (app/rate_limit.py).

Context: the API has no authentication (accepted-risk decision for this project's
scope). Without a request cap, nothing stops an unauthenticated caller from
enumerating CASE-xxxxxxxx ids or hammering LLM-backed endpoints without limit.
"""

from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from app.config import settings
from app.rate_limit import limiter

client = TestClient(fastapi_app)


def test_requests_within_the_limit_all_succeed():
    limiter.reset()
    for _ in range(5):
        response = client.get("/health")
    # /health is explicitly exempt from rate limiting — never 429s.
    assert response.status_code == 200


def test_exceeding_the_per_minute_limit_returns_429_with_retry_after(monkeypatch):
    limiter.reset()
    monkeypatch.setattr(settings, "rate_limit_per_minute", 3)

    statuses = [client.get("/api/v1/kadi/cases/CASE-doesnotexist").status_code for _ in range(5)]

    assert statuses[:3] == [404, 404, 404]
    assert 429 in statuses[3:]
    limited_index = statuses.index(429)
    response = client.get("/api/v1/kadi/cases/CASE-doesnotexist")
    assert response.status_code == 429
    assert "retry_after_seconds" in response.json()
    assert response.headers.get("Retry-After") is not None
    del limited_index  # only used to document intent above


def test_rate_limit_is_scoped_per_client_not_global(monkeypatch):
    """Different client IPs must not share one bucket — otherwise one caller could
    deny service to every other caller behind the same reverse proxy IP is a known,
    disclosed limitation, but two genuinely distinct source IPs must not collide."""
    limiter.reset()
    monkeypatch.setattr(settings, "rate_limit_per_minute", 2)

    allowed_a1, _ = limiter.check("1.2.3.4")
    allowed_a2, _ = limiter.check("1.2.3.4")
    allowed_a3, _ = limiter.check("1.2.3.4")
    allowed_b1, _ = limiter.check("5.6.7.8")

    assert (allowed_a1, allowed_a2, allowed_a3) == (True, True, False)
    assert allowed_b1 is True


def test_limiter_state_does_not_grow_unbounded():
    """Mirrors the existing processing_status bound (#14.3) — an in-memory client map
    must not become its own unbounded-memory denial-of-service vector."""
    limiter.reset()
    from app.rate_limit import _MAX_TRACKED_CLIENTS

    for i in range(_MAX_TRACKED_CLIENTS + 50):
        limiter.check(f"10.0.{i // 256}.{i % 256}")

    assert len(limiter._windows) <= _MAX_TRACKED_CLIENTS
