# ADR-029: Sign-in is required for every case and every module

## Status
**Accepted (maintainer directive 2026-11-25).** Supersedes the guest flow that **ADR-026** kept and
that **ADR-008** / **ADR-009** described. ADR-003 (bring your own document, zero document retention)
is unchanged: an account owns cases, never original files.

## Context
ADR-026 added accounts beside a guest flow, where a case opened without an account was reachable by
anyone holding its one-time token. The product directive requires that everything except public
information, registration, sign-in, password reset and email verification sit behind
authentication, enforced by the server.

## Decision
1. **Deny by default at the router.** `app/auth_gate.require_signed_in` is a dependency of the v1
   router. A request passes only if its path is in `PUBLIC_API_PATHS`, its route requires a staff
   credential, or it carries a live session. A new route is protected without further work.
2. **Staff credentials stay separate.** Routes guarded by `require_reviewer`,
   `require_institution` or `require_governance_admin` (ADR-011) authenticate those credentials
   themselves and do not also need a patient account. An *optional* credential does not count. The
   web page `/review` therefore opens without an account and shows only its credential form.
3. **Ownership only.** Case routes accept the owner's session and nothing else
   (`app/case_auth.require_case_access`). Query-string case tokens are removed.
4. **Existing guest cases can be claimed, not used.** `X-Case-Access-Token` is accepted by the claim
   route alone, so a signed-in person can move an older case into their account. Unclaimed cases
   still expire on the 90-day purge (ADR-010).
5. **Web.** `components/auth/RequireAccount` wraps `/app/*` and redirects to
   `/login?next=…` (allow-listed paths only). It is a convenience; the API is the control.
6. **Mobile** signs in with a bearer token kept in the device's secure store.

## Consequences
- Nobody can try the product without an account. The synthetic demo account (docs/DEMO_GUIDE.md)
  covers demonstrations.
- The web client needs an explicit `CORS_ORIGINS`, because browsers refuse credentialed requests to
  a wildcard. The default changed from `*` to `http://localhost:3000`.
- Where no email transport is configured (ADR-030), a forgotten password still cannot be recovered.
- Probes (`/health`, `/ready`) and `/metrics` are outside `/api/v1` and unchanged.
- Load tests and operator scripts now create or use an account.

## Verification
`apps/api/tests/test_mandatory_sign_in.py`, `test_case_authorization.py`, `test_case_ownership.py`.
