# ADR-026: User accounts and case ownership

## Status
**Accepted (maintainer decision 2026-11-23)** for the accounts decision (Wave 3 plan, decision D1:
"add real accounts"). Supersedes **ADR-008** and **ADR-009** *for signed-in use only*: the guest
flow those ADRs describe (no account, one-time `X-Case-Access-Token` per case) keeps working
unchanged. ADR-003 (bring your own document, zero document retention) is **not** changed: an
account owns cases, never original files.

Two sub-decisions are recorded here as **OPEN** and are **not implemented** (section 11):
**D1a** (derived figures outliving the 90-day purge) and the **email delivery channel**.

## Context
Until now the project had no user identity at all (ADR-008, accepted risk). ADR-009 added a
per-case capability token: whoever holds the token can use the case; lose the token and the case
is unreachable until the 90-day purge (ADR-010). That made a "my cases" list, cross-device access,
recovery and every account page in the Wave 3 information architecture impossible
(`docs/design/wave3-ux-architecture.md`, pages 08, 09–14, 16, 17, 20).

The maintainer chose to add real accounts (D1, 2026-11-23) with three constraints:
guest mode stays; zero document retention is unchanged; nothing new may talk to the network
(sending email is a new network boundary and needs its own decision).

Existing constraints this design must respect:
- **ADR-019:** exactly one API process. Still, sessions that must survive a restart live in the
  **database**, not in memory. (The per-IP limiter and the sign-in throttle stay in memory: losing
  them on restart only forgets slow-downs.)
- **ADR-020:** every table ships with an Alembic revision.
- **ADR-018:** use cases in `app/services`, thin routes, import contracts in `.importlinter`.
- **ADR-010:** cases expire after `CASE_TTL_DAYS` (90) and are erased by one cascade
  (`app/services/case_purge.py::purge_case`).
- The clinical reviewer and institution credentials (ADR-011, `app/clinical/auth.py`) are a
  separate identity system for staff and are untouched.

## Decision

### 1. Where accounts live
Accounts are shared infrastructure, like the case itself, so they belong to **Kadi**: tables are
prefixed `kadi_`, models live in `apps/api/app/models/accounts.py` (re-exported from
`app.models`), use cases in `app/services/accounts.py`, HTTP dependencies in
`app/account_auth.py`, routes in `app/api/v1/endpoints/accounts.py` mounted under
**`/api/v1/kadi/`** (`/kadi/auth/...`, `GET /kadi/cases`, `POST /kadi/cases/{id}/claim`). This
follows the `/api/v1/<module>/` convention; a separate `/accounts` prefix would invent a module
that has no package.

### 2. Tables (Alembic revision `0003_accounts`)
- `kadi_users`: `id`, `email` (normalised, **unique**), `password_hash`, `created_at`,
  `updated_at`, `email_verified_at`, `password_changed_at`. **No name, phone, date of birth,
  address or any other personal data.** (Failed-login state is not stored here; see section 7.)
  The email is the only personal datum and exists only because it is the login identifier.
- `kadi_sessions`: `id`, `user_id`, `token_hash` (SHA-256, unique), `transport`
  (`cookie`/`bearer`), `created_at`, `last_seen_at`, `expires_at`, `revoked_at`. No IP address,
  no user agent.
- `kadi_account_tokens`: `id`, `user_id`, `purpose` (`verify_email`/`reset_password`),
  `token_hash` (SHA-256, unique), `created_at`, `expires_at`, `used_at`.
- `kadi_cases.owner_user_id`: nullable FK to `kadi_users.id`, indexed. A case has at most one
  owner, so a column is simpler and cheaper to enforce than a link table. The FK has **no**
  `ON DELETE CASCADE`: deleting a user must go through `purge_case` for each owned case so every
  derived table is erased (a database cascade would delete only the case row).
- `bimanyay_cases.owner_user_id`, `bimanyay_grievances.owner_user_id`: nullable FK to
  `kadi_users.id`. BimaNyay can be used without a case; when a **signed-in** caller does that, the
  record is linked to the account so account deletion erases it (security review L4). Guest
  records and case-linked records keep `NULL` here (case-linked ones go with their case).

### 3. Password hashing
**stdlib `hashlib.scrypt`**, no new dependency. Per-user random 16-byte salt
(`secrets.token_bytes`), parameters stored in the hash string so they can be raised later:
`scrypt$<n>$<r>$<p>$<salt b64>$<key b64>`.

| Parameter | Default | Setting |
|---|---|---|
| N (CPU/memory cost) | 2^15 = 32768 | `PASSWORD_SCRYPT_N` (must be a power of two) |
| r (block size) | 8 | `PASSWORD_SCRYPT_R` |
| p (parallelism) | 3 | `PASSWORD_SCRYPT_P` |
| key length | 64 bytes | fixed |
| maxmem | 64 MiB | fixed (N=2^15, r=8 needs 32 MiB) |

N=2^15, r=8, p=3 is one of the equivalent-strength configurations the OWASP Password Storage
Cheat Sheet lists for scrypt (its first option is N=2^17, r=8, p=1). We take the 2^15 row so one
hash needs ~32 MiB rather than ~128 MiB on a small single-process host; operators can raise the
parameters without a migration. Argon2id would be
the first choice with a dependency (`argon2-cffi`); scrypt avoids adding one and is memory-hard.
Hashing runs in a worker thread (`asyncio.to_thread`) so it never blocks the event loop. A hash
made with older parameters is transparently re-hashed at the next successful login.

Passwords are NFKC-normalised before hashing so the same password typed on different keyboards
(Devanagari input methods, full-width forms) verifies identically.

**Password policy (length-based, NIST SP 800-63B style):** 12 to 128 characters after
normalisation, not only whitespace, not equal to the email address. No composition rules, no
forced rotation. Not implemented: a breached-password list check (needs a dataset or a network
call; recorded as a follow-up).

### 4. Sessions
- Opaque token, `secrets.token_urlsafe(32)` (256 bits). Only its SHA-256 hash is stored; a token
  is looked up by hash (a database index lookup on a hash of a 256-bit random value is not
  timing-sensitive in a useful way; a string comparison of a guessed token never happens).
- **Absolute lifetime** `SESSION_LIFETIME_HOURS` (default 168 = 7 days) and **idle timeout**
  `SESSION_IDLE_TIMEOUT_MINUTES` (default 120). `last_seen_at` is refreshed at most once a minute
  to avoid a write per request.
- **Revocation:** logout revokes the presented session; a password change revokes **every**
  session of the user and issues one fresh session to the caller (rotation); a password reset
  revokes every session and signs nobody in; account deletion deletes every session.
- Expired and revoked sessions and used or expired account tokens are deleted by the existing
  retention sweep (`app/case_retention.py`), so these tables do not grow without bound.

### 5. How clients carry the session
- **Web:** an `httpOnly`, `Secure`, `SameSite=Strict`, `Path=/` cookie, named
  `__Host-arogya_session` (the `__Host-` prefix forbids a `Domain` attribute, so a sibling
  subdomain cannot set or overwrite it). The token is **never** in a response body for cookie
  sessions, so script on the page (XSS) cannot read it. `SESSION_COOKIE_SECURE=false` (plain
  `http://` local development only; refused under `APP_ENV=production`) drops `Secure` and the
  prefix, naming it `arogya_session`.
- **CSRF:** `SameSite=Strict` already stops cross-site requests carrying the cookie. As a second,
  independent layer, every **state-changing** request (POST/PUT/PATCH/DELETE) that is
  authenticated **by the cookie**, and every login/registration request that carries an `Origin`,
  must send an `Origin` header listed in `AUTH_TRUSTED_ORIGINS` (default: the explicit entries
  of `CORS_ORIGINS`), or, **outside production only**, the API's own origin. Otherwise `403`.
  Browsers always send `Origin` on such requests, so this costs legitimate clients nothing.
  - The check runs only when the cookie maps to a **live** cookie session (review L7): a
    garbage, expired, revoked or planted cookie is ignored, so it can never turn a guest write
    into a `403`.
  - Under `APP_ENV=production` the API's own origin is **not** trusted automatically, because it
    is derived from the request's `Host` header (review L8). We do not add a *separate*
    mandatory `AUTH_TRUSTED_ORIGINS` for production: production already refuses to start with a
    wildcard `CORS_ORIGINS`, so the fallback is always an operator-written list of the same web
    origins, and a second required variable would break the existing Kubernetes manifests for no
    added safety. Set `AUTH_TRUSTED_ORIGINS` when the cookie-using origins differ from
    `CORS_ORIGINS`.
- **Cross-origin web deployments** (web on `:3000`, API on `:8000`) need an explicit
  `CORS_ORIGINS`: with the wildcard default, credentialed CORS is disabled (unchanged since the
  CORS hardening) and the browser will not send the cookie. Web and API must also be same-*site*
  for `SameSite=Strict` (true for `localhost:3000` / `localhost:8000`, and for
  `app.example.in` / `api.example.in`).
- **Mobile:** `Authorization: Bearer <token>`. The client asks for this at login with
  `"session_transport": "bearer"`; the token is returned once in the login response and the app
  keeps it in Expo SecureStore (Keychain / Keystore), never AsyncStorage. Bearer requests are not
  subject to the Origin check (no ambient credential, so no CSRF).
- A request that carries **both** is resolved from the `Authorization` header.
- An invalid, expired or revoked credential is treated as **no credential** on routes where
  signing in is optional (case creation, guest case routes), so a stale cookie never breaks the
  guest flow; routes that require an account answer `401`.

### 6. Case ownership
- **Guest flow unchanged.** A case created without a session is unowned and works exactly as in
  ADR-009: its token, returned once, authorises every `/cases/{case_id}/...` route.
- **Created while signed in:** the case is owned by that user from the start and **no case token
  is issued** (`access_token` is `null` in the creation response).
- **Claiming a guest case:** `POST /api/v1/kadi/cases/{case_id}/claim` with a valid session
  **and** the case's `X-Case-Access-Token`. On success the case is owned and its token hash is
  **cleared**. Claiming is idempotent for the owner; a case owned by someone else cannot be
  claimed (`403`). The claim is **one conditional `UPDATE`**
  (`... WHERE id = :id AND owner_user_id IS NULL AND access_token_hash = :presented_hash`); it
  must change exactly one row, so of two concurrent claims exactly one wins and the other gets
  `403`, never a false `claimed: true` (review M2).
- **An owned case does NOT accept its case token.** Justification: the point of ownership is that
  access follows the account (revocable, recoverable, protected by a password and throttling).
  A case token is a bearer capability that may already sit in browser storage, a copied link, a
  server log (the read-only `?access_token=` fallback, ADR-009) or a screenshot; leaving it valid
  would keep every ADR-009 leak path open on exactly the cases users chose to protect. Clearing
  it on claim also means a token copied before the claim stops working at that moment. The
  trade-off: a signed-in user cannot share one case with a second person by token. Sharing is
  not a Wave 3 requirement; if it becomes one it needs its own grant model, not a reused token.
- **Enforcement** is central: every case-scoped route already depends on
  `app.case_auth.require_case_access`, which now resolves the optional account principal first:

  | Case | Caller | Result |
  |---|---|---|
  | does not exist | anyone | `404` (unchanged: the 64-bit id is not a secret worth hiding) |
  | owned | owner's session | allowed |
  | owned | another account's session | `403` "not available to this account" |
  | owned | case token only | `403` "linked to an account; sign in" |
  | owned | nothing | `401` |
  | unowned | case token (with or without a session) | allowed, as ADR-009 |
  | unowned | session only / nothing / wrong token | `401` / `403`, as ADR-009 |

  BimaNyay's optional `case_id` link (`/bimanyay/analyze`, `/bimanyay/timeline`) uses the same
  rule through `app.case_auth.authorize_case`.
- **Accepted disclosure (review L6):** the `403`/`401` messages say that a case belongs to an
  account. Reaching that message needs the case's 64-bit random id, the same reasoning ADR-009
  uses for answering `404` before `401`; the clearer message is worth more to the real user
  than hiding a fact only an id holder can ask about.
- `GET /api/v1/kadi/cases` lists the signed-in user's **live** cases (not past `expires_at`),
  newest first, with ids and summary fields only. No case token is ever returned.
- **Owned cases still expire** after `CASE_TTL_DAYS` and are erased by the same sweep. Ownership
  does not extend retention (see D1a).

### 7. Abuse resistance
- **Account enumeration:** registration always answers `202` with the same body whether or not
  the email is taken (an existing account is not modified, and the password is hashed on both
  paths so timing is in the same class); login failures always answer `401` with one generic
  message, and a login for an unknown email still runs scrypt against a fixed dummy hash;
  verification and reset requests always answer `202` with the same body.
  Registration therefore does not sign the user in: the client calls login next.
  **Accepted residual timing (review L2):** the paths still differ by a few milliseconds of
  database work (an existing account inserts or updates rows; a reset request for a real
  account writes a token) next to ~300 ms of scrypt. Telling them apart needs many repeated,
  low-noise measurements, which the per-IP auth bucket (10/minute) makes slow; we accept it
  rather than add artificial padding.
- **Rate limits:** the existing limiter (`app/rate_limit.py`) gains a second, stricter bucket per
  client IP, `AUTH_RATE_LIMIT_PER_MINUTE` (default 10), shared by register, login, verification
  and reset requests and confirmations, password change and account deletion (both check the
  current password, so a stolen session cannot guess it faster than a login could). The global `RATE_LIMIT_PER_MINUTE` still applies.
- **Sign-in throttle per (account, client IP), not a lockout** (`app/services/login_throttle.py`;
  replaces the first version's per-account hard lock, which let anyone keep a victim locked out
  indefinitely by sending wrong passwords — review M1):
  - wrong passwords are counted per **(user id, client IP)**, so an attacker slows down only
    their own IP for that account; the real user on another network signs in normally;
  - failures **expire**: a pair with no failure for `LOGIN_FAILURE_WINDOW_MINUTES` (15) starts
    over, and a successful sign-in clears it;
  - after `LOGIN_FREE_FAILURES` (5) failures each further attempt from that pair must wait an
    **increasing delay** (1 s, 2 s, 4 s, … capped at `LOGIN_MAX_DELAY_SECONDS`, 900). An attempt
    inside the delay gets the **same generic `401`** (and still spends one scrypt), so the
    throttle reveals neither existence nor the correct password;
  - **wrong current passwords** on `POST /auth/password` and `DELETE /auth/me` count toward the
    same pair (review L3), so a stolen session cannot guess the password faster than a login;
  - in memory and bounded (10 000 pairs, least-recently-used eviction), like the per-IP limiter;
    no client IP is persisted. Residual risk: an attacker spread over many IPs gets
    `LOGIN_FREE_FAILURES` fast guesses per IP per window, bounded further by the per-IP auth
    bucket and scrypt cost; a per-account global ceiling was rejected because it is the
    lockout lever again.
- **Constant-time comparisons** (`hmac.compare_digest`) for password keys and case-token hashes.
- **No secrets in logs, URLs or error payloads:** passwords and tokens travel only in JSON bodies
  or headers; validation errors on `/kadi/auth/*` routes are returned **without** the submitted
  `input` value; the `arogyarakshak.accounts` logger never records an email address, password or
  token (user ids only).

### 8. Email verification, password reset and the mail transport
- Tokens are consumed with one conditional `UPDATE ... SET used_at = :now WHERE token_hash = :h
  AND purpose = :p AND used_at IS NULL AND expires_at > :now`, and the request proceeds only if
  exactly one row changed, so two concurrent uses cannot both succeed (review L1). A reset is
  consumed only after the new password passes the policy, so a rejected password leaves the
  token usable.
- Tokens are 256-bit, single-use, hashed (SHA-256), and expire:
  verification `ACCOUNT_VERIFICATION_TOKEN_TTL_HOURS` (24), reset
  `PASSWORD_RESET_TOKEN_TTL_MINUTES` (30). Issuing a new token voids earlier unused tokens of the
  same purpose. Tokens are confirmed with a JSON body (`POST .../confirm`), never a query string.
  When an email channel exists, links must carry the token in the URL **fragment** (`#token=`),
  which browsers never send to a server, and the page posts it.
- `MailTransport` (`app/services/mail.py`) is an interface; the only shipped implementation is
  **`disabled`** (`MAIL_TRANSPORT=disabled`, the only accepted value): it delivers nothing and
  logs only that a message of a given purpose was not delivered. Tests inject an in-memory
  transport to exercise the full flow.
- **Consequence while disabled:** verification and reset cannot reach a real user. Accounts work
  without verification (signing in does not require a verified email; `GET /kadi/auth/me`
  reports `email_verified`), and a user who forgets their password cannot recover the account.
  Their cases still expire after 90 days. This is stated in the UI requirements for M4.

### 9. Account deletion = erasure
`DELETE /api/v1/kadi/auth/me` (requires the current password in the body) erases, in one
transaction: every owned case through `purge_case` (the ADR-010 cascade, including clinical
records and BimaNyay links), every session, every account token and the user row. Unowned guest
cases are unaffected.

### 10. Threat model change versus ADR-008 / ADR-009
| | Before (ADR-008/009) | Now, signed in |
|---|---|---|
| Asset added | — | email addresses, password hashes, session tokens |
| Case access | possession of a bearer token | account session; case token disabled once owned |
| Leaked case token | full access until purge | useless once the case is owned |
| Lost token / device | case unreachable | sign in elsewhere (cross-device) |
| New attacks | — | credential stuffing and guessing (per-IP bucket + per-(account, IP) increasing delay + scrypt), account enumeration (uniform responses), session theft by XSS (httpOnly cookie), CSRF (SameSite=Strict + Origin check), scrypt CPU/memory exhaustion (per-IP bucket, single process), account squatting on someone else's email (**open until verification can be delivered**) |
| Erasure | per case, by token holder | per case, plus whole account |
| Data minimisation | no personal identity | one email address per account, erased with the account |

Unchanged: no uploaded document is stored (ADR-003); cases expire (ADR-010); per-IP limiting is
in-memory and per process (ADR-008); the reviewer/institution credentials (ADR-011).

### 11. OPEN sub-decisions (recorded, NOT implemented)
- **D1a: derived figures beyond the 90-day purge.** Long-term spending views would need amounts,
  dates and categories (never documents) to outlive `purge_case`. Not decided. Until it is,
  **owned cases expire exactly like guest cases**, `GET /kadi/cases` lists only live cases, and
  nothing is copied out of a case before it is purged. Deciding D1a needs: which fields, explicit
  consent, its own retention period and erasure path, and an update to ADR-010.
- **Email delivery channel.** Sending mail is a new network boundary (AGENTS.md network rule).
  Options: an SMTP relay the operator runs; a transactional email provider; or no email with an
  operator-assisted reset. Not decided; only `MAIL_TRANSPORT=disabled` exists. Deciding it needs a
  new ADR (or an amendment here), the network-boundary flag, a sender-domain plan (SPF/DKIM), and
  turning on "require verified email" for sensitive actions.
  **Email squatting (review L5) stays open until then:** anyone can register an address they do
  not own, and the real owner cannot take it over. Required fix once mail exists: either require
  a verified address before an account can sign in, or let a **verified** registration of the
  same address take over (and wipe) an account that never verified it.

## Consequences
### Positive
- Real, revocable, recoverable-in-principle access; a case list across devices; a leaked case
  token stops mattering once a case is claimed; whole-account erasure.
- No new dependency (stdlib scrypt, `secrets`, `hmac`), no new service, no network.
- Guest flow, consent (ADR-007), retention (ADR-010) and document handling (ADR-003) unchanged.

### Negative
- New personal data (email) and new attack surface (section 10).
- Without an email channel: no verification, no self-service recovery, and anyone can register
  any address (squatting). Disclosed, not hidden.
- Cookie sessions for a cross-origin web client need explicit `CORS_ORIGINS` and same-site
  hosting.
- A signed-in user cannot hand a case to someone else by token.
- Per-IP auth limits are in-memory (lost on restart), like the existing limiter.

## Follow-up
Frontend M4 (sign-in pages, cookie use with `credentials: "include"`, claim flow, case list);
mobile bearer storage in SecureStore; D1a; email channel; breached-password check; optional
"sign out other devices" listing.
