# Wave 3 — MA accounts backend: handoff

Branch `wave3/ma-accounts` (from `wave3/integration` at `6e5d48b`), worktree `D:\wt\w3-ma-accounts`.
Not pushed. `PROJECT_CONTEXT.md` and `CHANGELOG.md` are **not** edited (integrator's job).
No `packages/*` change, so the main checkout's editable installs were fine for testing.

## Design decisions (full record: ADR-026)

- **ADR-026 "User accounts and case ownership"**, status *Accepted (maintainer decision
  2026-11-23)*. ADR-008 and ADR-009 status lines now say "superseded for signed-in use by ADR-026"
  (content untouched; both stay in force for guest cases).
- **Placement:** accounts are Kadi shared infrastructure. Tables `kadi_users`, `kadi_sessions`,
  `kadi_account_tokens`, plus nullable `kadi_cases.owner_user_id` (FK, indexed, no DB cascade:
  deletion goes through `purge_case`). Routes under `/api/v1/kadi/`.
- **Passwords:** stdlib `hashlib.scrypt`, per-user 16-byte salt, N=2^15 r=8 p=3 (an OWASP
  equivalent-strength row, ~32 MiB), params stored in the hash and upgraded at next login,
  NFKC normalisation, hashing in a worker thread. Policy 12–128 chars, not only spaces, not the
  email. No new dependency.
- **Sessions:** 256-bit opaque tokens, SHA-256 hash stored, 7-day absolute + 120-min idle,
  `last_seen_at` refreshed at most once a minute; revoked on logout, every session revoked on
  password change (caller gets a fresh one) and reset, deleted on account deletion; bound to
  their transport.
- **Web:** `__Host-arogya_session` cookie, httpOnly + Secure + SameSite=Strict; Origin check on
  every cookie-authenticated write and on browser logins (`AUTH_TRUSTED_ORIGINS`, default the
  explicit `CORS_ORIGINS`, plus the API's own origin). **Mobile:** `Authorization: Bearer`,
  token returned once with `"session_transport": "bearer"`.
- **Ownership:** guest flow unchanged. Created signed in → owned, `access_token: null`.
  `POST /kadi/cases/{id}/claim` (session + case token) → owned, token hash cleared.
  **An owned case refuses its case token** (justified in ADR-026 §6: leaked-token paths stay
  closed; trade-off: no token sharing of owned cases). One rule in
  `app.case_auth.authorize_case`, used by `require_case_access` (every case route) and BimaNyay's
  optional `?case_id=` link.
- **Enumeration resistance:** uniform 202 for register / verification request / reset request,
  uniform 401 for every login failure, one scrypt derivation on every path (tested by counting).
- **Rate limits:** a stricter `auth:<ip>` bucket (10/min) inside the existing limiter (so the
  conftest reset covers it); per-account pause after 10 failures for 15 min that answers the
  same generic 401.
- **Mail:** `MailTransport` protocol, `DisabledMailTransport` (the only configurable value,
  `MAIL_TRANSPORT=disabled`), `InMemoryMailTransport` for tests via the `get_mail_transport`
  dependency. Logs purpose + user id only.
- **Housekeeping:** the retention loop also deletes revoked/expired/idle sessions and used or
  expired account tokens.
- **Error payloads:** `/kadi/auth/*` validation errors drop `input`/`ctx`; the HTTP exception
  handler now forwards deliberate headers (used for `Retry-After` on the auth bucket).

## Files

New: `apps/api/app/account_auth.py`, `apps/api/app/services/{accounts,passwords,mail}.py`,
`apps/api/app/models/accounts.py`, `apps/api/app/api/v1/endpoints/accounts.py`,
`apps/api/migrations/versions/0003_accounts.py`, `apps/api/tests/{test_accounts,test_case_ownership,account_helpers}.py`,
`docs/architecture/decisions/ADR-026-user-accounts-and-case-ownership.md`, `docs/api/accounts.md`, this file.

Changed: `app/case_auth.py` (ownership rule, `authorize_case`), `app/config.py` (13 settings,
scrypt validation, production error for `SESSION_COOKIE_SECURE=false`), `app/models/{kadi,__init__}.py`,
`app/services/case_ingestion.py` (`create_case_record(owner_user_id=...)`),
`app/api/v1/endpoints/kadi/{cases,schemas}.py` (owned case creation; `access_token` nullable, `owned`),
`app/api/v1/endpoints/bimanyay.py` (shared rule), `app/api/v1/api.py`, `app/rate_limit.py`
(per-bucket limit), `app/case_retention.py` (account sweep), `app/main.py` (see above),
`.importlinter` (new modules), `apps/api/tests/conftest.py` (appended: global cheap-scrypt fixture,
`clock`, `outbox`, `relaxed_auth_limit`; network guard and `no_groq_key` untouched),
`apps/api/tests/test_migrations.py` (legacy-adoption test now builds the real 0001 baseline; the old
"today's models minus one table" setup carried the new `owner_user_id` column),
`docs/api/{openapi.json,overview.md,compatibility.md}`, the three generated `schema.d.ts` copies
(`npm run generate`), `docs/configuration/environment-variables.md`, `.env.example`,
`docs/architecture/module-boundaries.md`, `docs/development/troubleshooting.md`,
ADR-008/009 status lines.

## Endpoints (all `/api/v1/kadi`)

`POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`,
`POST /auth/password`, `POST /auth/verification/request`, `POST /auth/verification/confirm`,
`POST /auth/password-reset/request`, `POST /auth/password-reset/confirm`, `DELETE /auth/me`,
`GET /cases`, `POST /cases/{case_id}/claim`. Details and the access table: `docs/api/accounts.md`.

## Verification

- Full backend suite, one invocation from the worktree root:
  `D:/FinalYearProject/Arogyarakshak/.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider`
  → **RESULT_PLACEHOLDER**
- New tests: `test_accounts.py` (49) and `test_case_ownership.py` (56, of which 43 are the
  ownership sweep over **every** route whose dependency tree contains `require_case_access`,
  found automatically: owner allowed, other account 403, case token alone 403, nobody 401).
- `test_migrations.py` also run against a throwaway PostgreSQL 16 container
  (`MIGRATION_TEST_DATABASE_URL`): 7 passed (upgrade = models, downgrade to empty, legacy adoption).
- `PYTHONPATH=apps/api lint-imports`: 5 contracts kept, 0 broken.
- `ruff check apps/api packages --select=E9,F63,F7,F82 --target-version=py311` (the CI selection): clean.
- `npm install`, `npm run generate`, `npm run check:generated` (3 passed), `npm test` (63 passed).
- Smoke test: uvicorn on `127.0.0.1:8100` against a throwaway Postgres 16 container
  (`SCHEMA_MANAGEMENT=migrate` → `/health/ready` revision `0003_accounts`,
  `SESSION_COOKIE_SECURE=false` because it was plain http, `CORS_ORIGINS=http://localhost:3000`).
  register 202 → same 202 for the same address in another case → login wrong password and unknown
  email both the identical 401 → cookie login 200 (`HttpOnly; SameSite=strict; Path=/`, token null)
  → `/auth/me` 200 → create case with web Origin 201 `owned:true, access_token:null` → same with
  an untrusted Origin 403 → owned case read: cookie 200, nothing 401 → guest case created and
  claimed 200 → its old token 403 → `GET /cases` lists both, no tokens → logout 204 → `/me` and
  `/cases` 401 → bearer login + `/me` 200 → reset request 202 (log: "not delivered") → delete
  account 200 `cases_erased: 2` → both cases 404. The server log contained no email address and
  no password. Server stopped, container removed, temp files deleted.

## Not verified

- No browser was used: cookie behaviour with a real browser (especially `__Host-`/`Secure` on
  `http://localhost`, and `EventSource` with `withCredentials`) is untested; M4 must check it.
- Timing equality is tested as "same number of scrypt derivations per path", not by measuring
  wall-clock distributions.
- The default scrypt cost was only exercised in the smoke test (tests use N=2^10, p=1); measured
  roughly 0.3–0.4 s per login on this machine.
- Mobile SecureStore storage is a recommendation in the ADR; nothing in `apps/mobile` changed.
- Concurrent duplicate registration (unique-constraint race) has a code path but no test.

## Open items

1. **D1a** (derived figures beyond the 90-day purge): open, not implemented. Owned cases expire
   exactly like guest cases; `GET /cases` shows live cases only.
2. **Email delivery channel:** open, not implemented (new network boundary). Until decided:
   no verification or self-service reset for real users, email squatting is possible, sign-in
   does not require a verified address.
3. **Frontend M4:** sign-in/register/reset pages, `credentials: "include"` on every web fetch,
   `EventSource(..., { withCredentials: true })`, handling `access_token: null` / `owned: true`
   on case creation, a "save this case to my account" claim flow for guest cases, the server-side
   case list (`GET /kadi/cases`) instead of `sessionStorage` for signed-in users, account
   deletion UI. Mobile: bearer login, SecureStore, `Authorization` header in `apps/mobile/src/api`.
4. **Deployment config:** for cookie sessions the web origin must be in `CORS_ORIGINS` (and/or
   `AUTH_TRUSTED_ORIGINS`); `docker-compose.yml` does not forward `CORS_ORIGINS`,
   `SESSION_COOKIE_SECURE` or `AUTH_TRUSTED_ORIGINS` to the `api` service today (not changed
   here: infra-owned file). Plain-http non-localhost hosts need `SESSION_COOKIE_SECURE=false`
   (development only).
5. Follow-ups named in the ADR: breached-password check, "sign out other devices" listing,
   case sharing grants (if ever needed), independent security review of this branch.
