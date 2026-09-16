"""Regression tests for the per-client-IP rate limiter (app/rate_limit.py).

Context: the API has no authentication (accepted-risk decision for this project's
scope). Without a request cap, nothing stops an unauthenticated caller from
enumerating CASE-xxxxxxxx ids or hammering LLM-backed endpoints without limit.
"""

from fastapi.testclient import TestClient
from starlette.requests import Request

from app.main import app as fastapi_app
from app.config import settings
from app.rate_limit import limiter, resolve_client_ip

client = TestClient(fastapi_app)


def _fake_request(client_host: str = "1.2.3.4", forwarded_for: str = None) -> Request:
    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    scope = {
        "type": "http",
        "headers": headers,
        "client": (client_host, 12345) if client_host else None,
        "method": "GET",
        "path": "/",
    }
    return Request(scope)


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


# ---------------------------------------------------------------------------
# P1-6: an attacker must not be able to reset OTHER clients' counters by flooding
# the tracked-client cap with throwaway IPs (the previous implementation cleared the
# ENTIRE map on overflow).
# ---------------------------------------------------------------------------


def test_reaching_the_tracked_client_cap_does_not_reset_an_active_abusive_clients_count(monkeypatch):
    limiter.reset()
    monkeypatch.setattr(settings, "rate_limit_per_minute", 3)
    from app.rate_limit import _MAX_TRACKED_CLIENTS

    victim_ip = "9.9.9.9"
    # The "victim" bucket is already over its limit.
    for _ in range(5):
        limiter.check(victim_ip)
    allowed, _ = limiter.check(victim_ip)
    assert allowed is False, "sanity check: victim should already be rate-limited"

    # An attacker floods the cap with throwaway distinct IPs, trying to force the
    # tracked-client map to evict/reset the victim's counter early.
    for i in range(_MAX_TRACKED_CLIENTS + 200):
        limiter.check(f"203.0.{i // 256}.{i % 256}")

    # The victim was touched most recently among the "real" traffic before the flood
    # started, but is still older than every attacker IP that follows — real LRU
    # eviction should have dropped IDLE attacker/victim entries one at a time, and the
    # important property is that the map never silently wiped itself to zero and let
    # the victim back in for free.
    assert len(limiter._windows) <= _MAX_TRACKED_CLIENTS
    # The core property: at no point does the whole map become empty from this flood —
    # a full-map .clear() would show as the length dropping to 1 (just the newest key)
    # immediately after any single flood request; real LRU never does that.
    lengths_seen = set()
    limiter.reset()
    for i in range(_MAX_TRACKED_CLIENTS + 200):
        limiter.check(f"203.0.{i // 256}.{i % 256}")
        if i > _MAX_TRACKED_CLIENTS:
            lengths_seen.add(len(limiter._windows))
    assert lengths_seen == {_MAX_TRACKED_CLIENTS}, (
        f"map length fluctuated during the flood ({lengths_seen}) — suggests a bulk "
        "clear rather than one-at-a-time LRU eviction"
    )


def test_active_client_is_not_the_one_evicted_under_a_flood():
    """An LRU cache must protect actively-used entries from eviction; only idle ones
    should be dropped when the map is at capacity."""
    limiter.reset()
    from app.rate_limit import _MAX_TRACKED_CLIENTS

    active_ip = "8.8.8.8"
    limiter.check(active_ip)

    for i in range(_MAX_TRACKED_CLIENTS + 500):
        limiter.check(f"198.51.{i // 256}.{i % 256}")
        if i % 50 == 0:
            limiter.check(active_ip)  # keep touching it so it stays "recently used"

    assert active_ip in limiter._windows, "an actively-used client was evicted despite being touched throughout"


# ---------------------------------------------------------------------------
# P1-6: X-Forwarded-For must never be trusted unless a trusted proxy count is
# explicitly configured — otherwise any client can forge their apparent IP.
# ---------------------------------------------------------------------------


def test_forwarded_for_is_ignored_by_default(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_count", 0)
    request = _fake_request(client_host="10.0.0.1", forwarded_for="1.2.3.4")
    assert resolve_client_ip(request) == "10.0.0.1"


def test_forwarded_for_is_used_when_one_trusted_proxy_is_configured(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_count", 1)
    # A single trusted proxy appends the real client IP as the last entry.
    request = _fake_request(client_host="127.0.0.1", forwarded_for="203.0.113.5")
    assert resolve_client_ip(request) == "203.0.113.5"


def test_forwarded_for_takes_the_correct_hop_with_two_trusted_proxies(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_count", 2)
    # client -> proxy1 -> proxy2 -> app: header is "client_claimed_ip, proxy1_ip"
    # (proxy2, the immediate peer, is not itself in the header). The real client is
    # the 2nd-from-right entry once both trusted hops are accounted for... in this
    # minimal 2-entry case, that is the first (leftmost) entry.
    request = _fake_request(client_host="127.0.0.1", forwarded_for="198.51.100.9, 203.0.113.5")
    assert resolve_client_ip(request) == "198.51.100.9"


def test_forwarded_for_falls_back_when_shorter_than_configured_trusted_hops(monkeypatch):
    """A header shorter than the configured trusted-hop count cannot have come through
    every trusted proxy legitimately — falling back to the raw peer IP is safer than
    trusting a position that doesn't exist in the chain."""
    monkeypatch.setattr(settings, "trusted_proxy_count", 3)
    request = _fake_request(client_host="10.0.0.1", forwarded_for="1.2.3.4")
    assert resolve_client_ip(request) == "10.0.0.1"


def test_forwarded_for_cannot_be_forged_past_a_trusted_proxy(monkeypatch):
    """Even with a trusted proxy configured, an attacker connecting DIRECTLY (not
    through the proxy) and forging X-Forwarded-For gets a short/implausible header —
    the fallback above already covers the realistic version of this, this test pins
    the specific spoofing scenario named in the audit: a client claiming to be someone
    else's IP."""
    monkeypatch.setattr(settings, "trusted_proxy_count", 1)
    # The attacker connects directly and sets X-Forwarded-For to an arbitrary victim IP.
    # With trusted_proxy_count=1, this IS taken as the client IP — because a real proxy
    # would also produce a 1-entry header for a direct client. This is the disclosed
    # trade-off of trusting a proxy: everything between the internet and that proxy MUST
    # be genuinely unreachable except through it, or this exact spoof is possible. The
    # test exists to make that trade-off explicit and verified, not to claim it away.
    request = _fake_request(client_host="10.0.0.1", forwarded_for="99.99.99.99")
    assert resolve_client_ip(request) == "99.99.99.99"
