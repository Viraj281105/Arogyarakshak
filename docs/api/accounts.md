# Accounts and case ownership API (ADR-026)

All routes are under `/api/v1/kadi`. The guest flow (create a case, keep its one-time
`X-Case-Access-Token`) is unchanged; accounts are optional. Decision record:
[`ADR-026`](../architecture/decisions/ADR-026-user-accounts-and-case-ownership.md).

Error bodies keep the project shape `{"detail": ..., "message": ...}`. Validation errors on
`/kadi/auth/*` never include the submitted values (`input`/`ctx` are removed).

## Carrying the session

| Client | How | Notes |
|---|---|---|
| Web | Cookie `__Host-arogya_session` (`httpOnly`, `Secure`, `SameSite=Strict`, `Path=/`) set by `POST /auth/login` with `"session_transport": "cookie"` (default). Send requests with `credentials: "include"`. | The token is never in a response body. Every POST/PUT/PATCH/DELETE sent with the cookie must carry an `Origin` that is the API's own origin or listed in `AUTH_TRUSTED_ORIGINS` (default: explicit `CORS_ORIGINS`), else `403`. A cross-origin web app needs an explicit `CORS_ORIGINS`. |
| Mobile | `Authorization: Bearer <token>`; get the token from `POST /auth/login` with `"session_transport": "bearer"`. | Store it in Expo SecureStore. No Origin check. |

A session is bound to its transport (a cookie token is not accepted as a bearer token).
Lifetime: `SESSION_LIFETIME_HOURS` (168) absolute, `SESSION_IDLE_TIMEOUT_MINUTES` (120) idle.
An invalid or expired credential is ignored on routes where signing in is optional (case
creation, guest case routes) and is `401` where an account is required.

## Routes

| Method | Route | Auth | Body | Success | Failures |
|---|---|---|---|---|---|
| `POST` | `/auth/register` | none (auth bucket) | `{email, password}` | `202` `{status:"accepted", message}` — **same** for a new and a taken address; does not sign in | `422` invalid email / password policy; `429`; `403` untrusted browser Origin |
| `POST` | `/auth/login` | none (auth bucket) | `{email, password, session_transport?: "cookie"\|"bearer"}` | `200` `{user, session:{transport, expires_at, idle_timeout_minutes}, token}` (`token` only for bearer) | `401` generic for unknown email, wrong password and a paused account; `429`; `403` untrusted Origin |
| `POST` | `/auth/logout` | session | — | `204`, session revoked, cookie cleared | `401` |
| `GET` | `/auth/me` | session | — | `200` `{id, email, email_verified, email_verified_at, created_at}` | `401` |
| `POST` | `/auth/password` | session (auth bucket) | `{current_password, new_password}` | `200` like login: **every** session revoked, one fresh session for the caller (new cookie or new `token`) | `403` wrong current password; `422` policy; `401` |
| `POST` | `/auth/verification/request` | none (auth bucket) | `{email}` | `202`, same body whether or not an account exists | `429` |
| `POST` | `/auth/verification/confirm` | none (auth bucket) | `{token}` | `200` `{status:"verified"}` | `400` invalid, used or expired |
| `POST` | `/auth/password-reset/request` | none (auth bucket) | `{email}` | `202`, same body whether or not an account exists | `429` |
| `POST` | `/auth/password-reset/confirm` | none (auth bucket) | `{token, new_password}` | `200` `{status:"password_reset"}`; every session revoked; does not sign in | `400` token; `422` policy (token stays usable) |
| `DELETE` | `/auth/me` | session (auth bucket) | `{password}` | `200` `{deleted:true, cases_erased}`; owned cases erased through the purge cascade, sessions and tokens deleted, cookie cleared | `403` wrong password; `401` |
| `GET` | `/cases` | session | — | `200` `{cases:[{id, status, consent_opt_in, total_charged, created_at, updated_at, expires_at}]}` — live owned cases, newest first, never a token | `401` |
| `POST` | `/cases/{case_id}/claim` | session **and** `X-Case-Access-Token` | — | `200` `{id, owned:true, claimed}` (`claimed:false` if already yours); the case token stops working | `401` no session / no token; `403` wrong token or owned by another account; `404` |

"Auth bucket": `AUTH_RATE_LIMIT_PER_MINUTE` (10) requests per client IP per minute across
these routes (including the two that check the current password), on top of the global limit. `429` carries `Retry-After`.

Password policy: 12 to 128 characters after Unicode NFKC normalisation, not only spaces, not
the email address. No composition rules.

Email delivery is **not configured** (`MAIL_TRANSPORT=disabled`, an open decision): request
routes create the token and answer `202`, but nothing is sent, so verification and reset
cannot complete for a real user yet. Signing in does not require a verified email.

## Case creation and case routes

`POST /kadi/cases` with a session creates an **owned** case: the response has
`"owned": true` and `"access_token": null`. Without a session it is unchanged
(`"owned": false`, a token returned once).

Every `/cases/{case_id}/...` route in every module (and BimaNyay's optional `?case_id=` link)
applies one rule (`app.case_auth.authorize_case`):

| Case | Caller | Result |
|---|---|---|
| owned | owner's session | allowed |
| owned | another account | `403` "This case is not available to the signed-in account." |
| owned | case token only | `403` "…its case access token no longer works. Sign in…" |
| owned | nothing | `401` |
| unowned (guest) | its token, with or without a session | allowed (ADR-009) |
| unowned | session only / nothing | `401`; wrong token `403` |

Owned cases still expire after `CASE_TTL_DAYS` and are purged like guest cases (D1a is open).
For an owned case the SSE stream (`GET /cases/{id}/stream`) and PDF downloads work with the
cookie (`EventSource` with `withCredentials`) or the bearer header; `?access_token=` cannot
open an owned case.
