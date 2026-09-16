"""Per-client-IP request rate limiting.

In-memory fixed-window counter, consistent with the existing single-process
`processing_status` store in `app/api/v1/endpoints/kadi.py`: bounded, evicted, and
explicitly documented as not shared across workers. A multi-worker or multi-instance
deployment would need this backed by Redis or the database instead (see the CI
guardrails / ADR notes on `processing_status` for the same caveat) — recorded as a
known limitation, not silently assumed to scale.

This exists because the API has no authentication beyond per-case tokens (ADR-008,
ADR-009). Without a request cap, an unauthenticated caller can enumerate CASE-xxxxxxxx
ids or hammer the LLM-backed extraction/appeal endpoints without limit.

P1-6 audit findings fixed here (of the PREVIOUS implementation, verified against the
actual code, not assumed from the report):
- CONFIRMED eviction was `self._windows.clear()` on hitting the tracked-client cap —
  an attacker (or an accidental burst from many distinct IPs) could reach the cap and
  wipe every OTHER client's counters in one request, resetting rate limits for
  everyone including active abusers. Replaced with real LRU eviction (oldest-accessed
  single entry dropped, not the whole map) via collections.OrderedDict.
- CONFIRMED the client IP was always `request.client.host` with no reverse-proxy
  awareness — behind any proxy (nginx, a load balancer, Docker's own bridge in some
  setups), every real client shares the proxy's IP and gets bucketed into ONE limit.
  Fixed with an opt-in, explicitly-trusted-hop-count X-Forwarded-For resolution
  (`resolve_client_ip`) — trusting that header by default would let ANY caller forge
  their apparent IP and evade or frame another client, so it is never consulted unless
  `TRUSTED_PROXY_COUNT` is deliberately configured above 0.
"""

import time
from collections import OrderedDict
from typing import Optional, Tuple

from starlette.requests import Request

from app.config import settings

# Hard ceiling on tracked clients so this cannot itself become an unbounded-memory
# vector under a burst from many distinct IPs (the same failure mode already fixed
# for `processing_status`).
_MAX_TRACKED_CLIENTS = 5000


def resolve_client_ip(request: Request) -> str:
    """Resolves the client IP to rate-limit against.

    With `settings.trusted_proxy_count == 0` (the default — "not behind a trusted
    proxy"), this is ALWAYS `request.client.host`: X-Forwarded-For is attacker-
    controlled input from an untrusted client's own request and is never consulted at
    this setting, full stop.

    When a deployment sets `trusted_proxy_count = N` (meaning: N reverse proxies this
    operator controls sit between the internet and this API, each appending the
    connecting peer's IP to X-Forwarded-For), the real client IP is the Nth-from-the-
    right entry in that header — everything to its right was appended by a trusted hop;
    everything to its left (including the claimed "client IP" itself) is still
    self-reported by whoever made the original request and MUST NOT be trusted, which
    is exactly why this only reads the Nth-from-right position, never the first entry.
    """
    fallback = request.client.host if request.client else "unknown"

    if settings.trusted_proxy_count <= 0:
        return fallback

    forwarded_for = request.headers.get("X-Forwarded-For")
    if not forwarded_for:
        return fallback

    hops = [h.strip() for h in forwarded_for.split(",") if h.strip()]
    if len(hops) < settings.trusted_proxy_count:
        # Fewer hops than configured trusted proxies — the header is shorter than a
        # legitimately-proxied request would produce (e.g. spoofed, or a direct call
        # bypassing the proxy). Fall back rather than trust a position that doesn't exist.
        return fallback

    return hops[-settings.trusted_proxy_count]


class RateLimiter:
    """Fixed 60-second window, one counter per client key, bounded by real LRU eviction."""

    def __init__(self) -> None:
        self._windows: "OrderedDict[str, Tuple[int, int]]" = OrderedDict()

    def reset(self) -> None:
        """Clears all tracked state. Called between tests so limits from one test
        cannot leak into the next — the limiter is a module-level singleton shared
        across the whole pytest session, same as `processing_status`."""
        self._windows.clear()

    def check(self, client_key: str) -> Tuple[bool, int]:
        """Returns (allowed, retry_after_seconds). retry_after_seconds is 0 when allowed."""
        now = int(time.time())
        window_start = now - (now % 60)

        existing = self._windows.get(client_key)
        if existing is not None:
            # Touch: move to the most-recently-used end so an active client is never the
            # one evicted next.
            self._windows.move_to_end(client_key)
            start, count = existing
        else:
            start, count = window_start, 0
            if len(self._windows) >= _MAX_TRACKED_CLIENTS:
                # Evict exactly the single least-recently-used entry — never the whole
                # map. A burst of distinct IPs can only ever push out other IDLE
                # clients' state one at a time, not wipe every active client's counters.
                self._windows.popitem(last=False)

        if start != window_start:
            start, count = window_start, 0

        count += 1
        self._windows[client_key] = (start, count)

        if count > settings.rate_limit_per_minute:
            return False, max(1, start + 60 - now)
        return True, 0


limiter = RateLimiter()
