# Accounts and case ownership API (ADR-026, ADR-029)

All routes are under `/api/v1/kadi`. **Every `/api/v1` route needs a session** except the public
account routes (`config`, `register`, `login`, the two `verification` and the two `password-reset`
routes) and routes that require a staff credential (reviewer, institution, operator key). Records:
[`ADR-026`](../architecture/decisions/ADR-026-user-accounts-and-case-ownership.md),
[`ADR-029`](../architecture/decisions/ADR-029-mandatory-sign-in.md),
[`ADR-030`](../architecture/decisions/ADR-030-gmail-account-email.md).

Error bodies keep the project shape `{"detail": ..., "message": ...}`. Validation errors on
`/kadi/auth/*` never include the submitted values (`input`/`ctx` are removed).

## Carrying the session

| Client | How | Notes |
|---|---|---|
| Web | Cookie `__Host-arogya_session` (`httpOnly`, `Secure`, `SameSite=Strict`, `Path=/`) set by `POST /auth/login` with `"session_transport": "cookie"` (default). Send requests with `credentials: "include"`. | The token is never in a response body. Every POST/PUT/PATCH/DELETE sent with a cookie of a **live** session must carry an `Origin` listed in `AUTH_TRUSTED_ORIGINS` (default: explicit `CORS_ORIGINS`) or, outside production only, the API's own origin; else `403`. A dead or unknown cookie is ignored. A cross-origin web app needs an explicit `CORS_ORIGINS`. |
| Mobile | `Authorization: Bearer <token>`; get the token from `POST /auth/login` with `"session_transport": "bearer"`. | Store it in Expo SecureStore. No Origin check. |

A session is bound to its transport (a cookie token is not accepted as a bearer token).
Lifetime: `SESSION_LIFETIME_HOURS` (168) absolute, `SESSION_IDLE_TIMEOUT_MINUTES` (120) idle.
An invalid or expired credential is treated as signed out: `401` on every protected route.

## Routes

| Method | Route | Auth | Body | Success | Failures |
|---|---|---|---|---|---|
| `POST` | `/auth/register` | none (auth bucket) | `{email, password}` | `202` `{status:"accepted", message}` — **same** for a new and a taken address; does not sign in | `422` invalid email / password policy; `429`; `403` untrusted browser Origin |
| `POST` | `/auth/login` | none (auth bucket) | `{email, password, session_transport?: "cookie"\|"bearer"}` | `200` `{user, session:{transport, expires_at, idle_timeout_minutes}, token}` (`token` only for bearer) | `401` generic for unknown email, wrong password and a throttled attempt; `429`; `403` untrusted Origin |
| `POST` | `/auth/logout` | session | — | `204`, session revoked, cookie cleared | `401` |
| `GET` | `/auth/config` | none | — | `200` `{email_delivery: boolean}` | `429` |
| `GET` | `/auth/me` | session | — | `200` `{id, email, email_verified, email_verified_at, created_at, is_demo, display_name}` | `401` |
| `POST` | `/auth/password` | session (auth bucket) | `{current_password, new_password}` | `200` like login: **every** session revoked, one fresh session for the caller (new cookie or new `token`) | `403` wrong current password; `422` policy; `401` |
| `POST` | `/auth/verification/request` | none (auth bucket) | `{email}` | `202`, same body whether or not an account exists | `429` |
| `POST` | `/auth/verification/confirm` | none (auth bucket) | `{token}` | `200` `{status:"verified"}` | `400` invalid, used or expired |
| `POST` | `/auth/password-reset/request` | none (auth bucket) | `{email}` | `202`, same body whether or not an account exists | `429` |
| `POST` | `/auth/password-reset/confirm` | none (auth bucket) | `{token, new_password}` | `200` `{status:"password_reset"}`; every session revoked; does not sign in | `400` token; `422` policy (token stays usable) |
| `DELETE` | `/auth/me` | session (auth bucket) | `{password}` | `200` `{deleted:true, cases_erased}`; owned cases erased through the purge cascade (and their in-memory progress), the account's own stand-alone BimaNyay records, sessions and tokens deleted, cookie cleared | `403` wrong password; `401` |
| `GET` | `/cases` | session | — | `200` `{cases:[{id, status, consent_opt_in, total_charged, created_at, updated_at, expires_at}]}` — live owned cases, newest first, never a token | `401` |
| `POST` | `/cases/{case_id}/claim` | session **and** `X-Case-Access-Token` | — | `200` `{id, owned:true, claimed}` (`claimed:false` if already yours); the case token stops working. This is the only route that accepts a case token. Atomic: of two concurrent claims one wins, the other gets `403` | `401` no session / no token; `403` wrong token or owned by another account; `404` |

"Auth bucket": `AUTH_RATE_LIMIT_PER_MINUTE` (10) requests per client IP per minute across
these routes (including the two that check the current password), on top of the global limit. `429` carries `Retry-After`.

Sign-in throttle: wrong passwords are counted per (account, client IP) for
`LOGIN_FAILURE_WINDOW_MINUTES` (15). After `LOGIN_FREE_FAILURES` (5) each further attempt from that
pair waits 1 s, 2 s, 4 s, … (max `LOGIN_MAX_DELAY_SECONDS`, 900); an attempt inside the delay gets the
same `401`. Wrong current passwords on `POST /auth/password` and `DELETE /auth/me` count too.
Another device or network is not affected, so an attacker cannot lock the real user out.

Password policy: 12 to 128 characters after Unicode NFKC normalisation, not only spaces, not
the email address. No composition rules.

Email delivery is off by default (`MAIL_TRANSPORT=disabled`): request routes create the token and
answer `202`, but nothing is sent, so verification and reset cannot complete. With `gmail_api`
(ADR-030, [setup](../configuration/email-gmail.md)) the link is mailed. Responses are the same for
known and unknown addresses. Signing in does not require a verified email.

## Case creation and case routes

`POST /kadi/cases` needs a session and creates a case owned by that account: `"owned": true`,
`"access_token": null`.

Every `/cases/{case_id}/...` route in every module (and BimaNyay's optional `?case_id=` link)
applies one rule (`app.case_auth`):

| Case | Caller | Result |
|---|---|---|
| any | no session | `401` |
| owned | owner's session | allowed |
| owned | another account | `403` |
| unclaimed (made before ADR-029) | any session | `403` until claimed with its token |

Cases expire after `CASE_TTL_DAYS` and are purged. The SSE stream and PDF downloads use the cookie
(`EventSource` with `withCredentials`) or the bearer header. No credential is accepted in a query
string.

## Action records (ADR-031)

Owner only. See [action-and-resolution](../features/action-and-resolution.md) for statuses and rules.

| Method | Route | Success | Failures |
|---|---|---|---|
| `GET` | `/cases/{case_id}/actions` | `200` `{actions:[…]}` | `401`, `403`, `404` |
| `POST` | `/cases/{case_id}/actions` | `201` action | `409` limit; `422` |
| `POST` | `/cases/{case_id}/actions/{action_id}/events` | `200` action | `404`; `409` impossible move, date or limit; `422` |
| `DELETE` | `/cases/{case_id}/actions/{action_id}` | `204` | `404` |
