# ADR-009: Per-Case Access Authorization (Token, Not Login)

## Status
Accepted

## Context
ADR-008 (Phase 4) raised case-id entropy from 32 to 64 bits and added per-IP rate
limiting, but explicitly recorded — as an accepted, disclosed risk — that neither control
is authorization: **any caller who obtained a case id by any means (a shared link, a
browser history entry, a referrer header, a server log line, guessing) could read and act
on that case's data indefinitely.** Every `/cases/{case_id}/...` route across all five
modules (Kadi, BillNyay, DaaviSetu, SchemeSetu, DawaCheck) trusted the id alone.

An independent adversarial security audit (2026-09-16) confirmed this as the top
unresolved finding (P0-1) and asked for the smallest REAL authorization boundary
compatible with the existing architecture — not more obscurity, not a full account
system unless nothing smaller would do.

## Decision
Every case now gets a high-entropy **access token** at creation time
(`secrets.token_urlsafe(32)`, 256 bits). Only its SHA-256 hash is persisted
(`KadiCase.access_token_hash`); the plaintext token is returned **exactly once**, in the
`POST /api/v1/kadi/cases` response body, and never echoed back by any later read.

Every case-scoped route (all `/cases/{case_id}/...` endpoints across all five modules —
see the full list in `app/case_auth.py`'s call sites) now depends on
`app.case_auth.require_case_access`, which:

1. Loads the case; 404s if it does not exist (existence is not treated as a secret worth
   hiding behind a uniform error — the case id is already a 64-bit random token an
   attacker would need to have guessed correctly to reach this check at all).
2. 401s if no token was presented (`X-Case-Access-Token` header, or `?access_token=`
   query parameter — the latter exists **only** because the browser's native
   `EventSource` API cannot set custom headers, and is used only by
   `GET /cases/{case_id}/stream`; every other route uses the header).
3. 403s if the presented token's hash does not match the stored one, using
   `hmac.compare_digest` (constant-time, so response timing cannot be used to
   brute-force a token character-by-character).
4. Otherwise returns the loaded `KadiCase` for the route to use.

**Authorization and consent are different, layered concerns**, not merged into one
check (`app/consent.py`'s docstring states this explicitly). `require_case_access` always
runs first: it answers "may this caller reach this case at all?" `require_case_consent`
(now a pure function taking the already-loaded case) answers a narrower question:
"may this case's context be shared *across modules*?" A case's own token holder can
always reach `GET /cases/{case_id}`; whether BillNyay/DaaviSetu/SchemeSetu/DawaCheck may
read that case's Kadi-extracted context is still gated by `consent_opt_in`, set once at
case creation, exactly as ADR-003 describes — that promise is unchanged by this ADR.

## What this deliberately is NOT
This is **not a user-account or login system.** There is still no concept of "user"
distinct from "whoever holds this case's token." Consequences, stated plainly:

- If the plaintext token is lost (browser storage cleared, app reinstalled, no
  cross-device sync), the case becomes **permanently unreachable** — there is no
  password reset, because there is no account to reset it on. This trade-off was
  accepted deliberately: a real account system (registration, login, password/session
  management, recovery flows) is a materially larger feature than a security hardening
  pass, and was explicitly out of scope for this remediation.
- Anyone who obtains the token by other means (a compromised device, a token logged
  insecurely by a future change) still has full access — a token is a capability, not an
  identity. This is the same trust model as an API key.
- The query-string fallback for the SSE stream route means that token can appear in
  server access logs and browser history on that one route. This is a known, narrower
  attack surface than every route trusting the case id alone, but it is not zero — flagged
  here rather than left implicit.

## Consequences

### Positive
- Closes the actual vulnerability (P0-1): a case id alone is no longer sufficient to read
  or act on a patient's data. Verified with adversarial tests
  (`apps/api/tests/test_case_authorization.py`) proving Case A's token cannot access
  Case B on read routes (`GET /cases/{id}`, `/resolutions`, `/graph`) and action routes
  spanning all five modules (upload, BillNyay audit/appeal, DaaviSetu claim, SchemeSetu
  income-profile/eligibility, DawaCheck benchmark, Kadi resolution feedback, ABDM import).
- No new standing infrastructure: no session store, no login UI, no password hashing
  library beyond stdlib `hashlib`/`hmac`/`secrets`. Consistent with the project's existing
  bounded-in-memory-store pattern (`processing_status`, the rate limiter) in spirit, though
  the token hash itself is persisted in Postgres/SQLite, not in memory.
- Existing frontend flow (create case → immediately use it) needed one addition: capture
  and hold the token from the creation response for the lifetime of that case's UI state.
  No redesign of the case lifecycle.

### Negative — explicitly accepted, not hidden
- No password/account recovery, ever, by design (see above).
- No true multi-device access to one case unless the token is deliberately shared (e.g.
  a QR code or copy-paste flow) — not built in this pass.
- Existing rows created before this migration (if any exist in a running deployment) have
  `access_token_hash IS NULL` and are **permanently unreachable** through any
  case-scoped route after this change deploys, because `require_case_access` treats a
  null/empty hash as "can never be authorized," never as "open access." For this
  project's stage (no real deployed user data), this is acceptable; a production rollout
  with real existing data would need either a migration that issues fresh tokens for
  existing open cases (with some side channel to deliver them) or a documented "old cases
  become inaccessible" cutover — recorded here so it is not silently rediscovered.
- Still single "layer" of secrecy: whoever holds the token has full read/write on that
  case, with no finer-grained permissions (e.g. "read-only sharing" is not supported).

## Follow-up
A real account system remains the correct eventual fix if this project moves toward
handling real patient data at scale — this ADR's token model is the compensating control
appropriate for the project's current stage, not a claim that it is production-grade
identity and access management.
