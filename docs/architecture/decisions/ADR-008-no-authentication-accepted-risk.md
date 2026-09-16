# ADR-008: No Authentication Layer — Accepted Risk, with Compensating Controls

## Status
Accepted

## Context
The API has never had an authentication or authorization layer. Any caller who knows or
guesses a `CASE-xxxxxxxx` case id can read that case's extracted entities and run every
module's audit/eligibility/appeal endpoints against it — nothing verifies the caller is the
patient who created the case. This has been documented as the top remaining security gap in
every audit pass to date (`docs/academic/presentations/ArogyaRakshak_Current_State_Audit.md`
§3.5, §6.4, §16.5).

## Problem
Building a real authentication layer (accounts, sessions/JWTs, per-case ownership checks on
every route, matching UI on both clients) is a multi-hour, multi-file feature — not a
hardening fix — for a project whose architecture, both clients, and every existing test were
built around unauthenticated, id-scoped case access. Doing it properly (not a token pasted
into `localStorage` with no real backing) would mean redesigning the case lifecycle, which is
out of scope for a hardening pass and was explicitly deferred by the project owner
(2026-09-15) in favour of lightweight compensating controls.

## Decision
We do **not** add an authentication layer in Phase 4. Instead we ship the controls that are
achievable without one:

1. **Case-id entropy raised from 32 to 64 bits.** `CASE-{secrets.token_hex(8)}` replaces
   `CASE-{uuid4().hex[:8]}` (`apps/api/app/api/v1/endpoints/kadi.py::create_case`). This
   raises the cost of blind guessing, not of a targeted or automated enumeration attack —
   entropy alone does not substitute for authentication.
2. **Per-client-IP rate limiting.** `app/rate_limit.py`, wired as FastAPI middleware in
   `app/main.py`. A fixed 60-second window, default 120 requests/client (`RATE_LIMIT_PER_MINUTE`
   env var), returns `429` with `Retry-After`. This bounds automated enumeration and abuse of
   the LLM-backed endpoints from a single source, but does **not** stop a low-and-slow or
   distributed attacker, and does not stop a legitimate-looking client from reading any case
   id it is handed.
3. **Consent remains the only per-case gate** (ADR-003, `app/consent.py`) — it verifies the
   *case* opted in, not that the *caller* is the patient. It is not a substitute for
   authentication and is not claimed to be one.

## Consequences
### Positive
- No architecture rewrite, no new standing infrastructure (Redis, session store, login UI)
  for a project-scope hardening pass.
- Both compensating controls are single-process, in-memory, and follow the same bounded-dict
  pattern already accepted for `processing_status` (§14.3 of the audit) — no new operational
  dependency.

### Negative — explicitly accepted, not hidden
- **Any caller who obtains a case id (e.g. from a shared link, a browser history entry, or a
  referrer header) can read and act on that case indefinitely.** There is no ownership check.
- Rate limiting is single-process and per-IP: it does not survive a multi-worker deployment
  without a shared store, and it does not stop an attacker distributed across many IPs.
- This ADR does **not** claim the system is safe to deploy with real patient data at scale.
  It records what was and was not done, and why, so the gap is not silently rediscovered.

## Follow-up
A real authentication layer (minimum: per-case ownership tied to a device or account
identity, enforced server-side on every Kadi-consuming route) remains the single highest-value
security item for any future phase beyond this project's scope.
