# Product evolution: sign-in, demo, action journey, localisation, accessibility

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (native, one session). Steps use checkboxes.

**Goal:** Evolve the six modules into one signed-in, trilingual patient journey (issue → evidence → action → response → outcome) without changing the architecture, brand or privacy model.

**Architecture:** Sign-in is enforced by one deny-by-default dependency on the v1 router. Actions and responses are a new Kadi-owned, case-scoped record set erased by the existing purge cascade. UI strings use English-source `t()` keys with Hindi and Marathi dictionaries loaded on demand.

**Tech Stack:** Existing only. No new runtime dependency. Gmail uses the HTTPS API over stdlib `urllib`.

**Spec:** the maintainer's "Product evolution" master directive (chat, 2026-11-25).

## Global Constraints

- No commit, push, reset or branch change. Stay on `wave3/transformation`.
- No redesign: tokens, fonts, logo geometry, illustrations and layout strategy are unchanged. No GSAP, Lottie or Rive.
- ADR-003 unchanged: no original document is stored; a response document goes through the existing transient upload and is referenced by SHA-256.
- No fabricated state: nothing says "Submitted"; every tracking event is `user_recorded` unless the system produced it.
- Web initial JS stays at or under 170 KB gzip per route; no ceiling raised.
- Database tables are prefixed `kadi_`; schema changes ship as Alembic revision `0004`.
- Hindi/Marathi is machine translation (by Claude, not Google), labelled as not reviewed by a native speaker.
- Network boundary: Gmail is disabled by default; no request leaves the machine unless an operator configures it.

## Review Focus

1. A signed-out request with a valid old case token: must get 401, not case data (Task 1).
2. A signed-in user posting an action to another user's case, or naming another case's document: 403 / 422 (Task 4).
3. An impossible tracking jump (`planned` → `response_received`): 409, nothing written (Task 4).
4. A missing or placeholder-mismatched Hindi/Marathi key: the completeness test fails (Task 6).
5. Password reset for an unknown address with Gmail on: same response, no timing-visible network call (Task 2).

## Tasks

### Task 1: Mandatory sign-in (API)
**Files:** create `apps/api/app/auth_gate.py`; modify `app/api/v1/api.py`, `app/case_auth.py`, `app/api/v1/endpoints/{kadi/cases,clinical_demo,bimanyay}.py`, `app/clinical/demo_control.py`; test `tests/test_mandatory_sign_in.py`.
**Produces:** `require_signed_in(request, principal)`; `PUBLIC_API_PATHS: frozenset[str]`; `create_case` needs a principal.
- [ ] Test: every `/api/v1` operation answers 401 signed out, except `PUBLIC_API_PATHS` and operations guarded by a staff credential.
- [ ] Test: unowned case with its token and no session → 401; with another session → 403; claim still works.
- [ ] Implement; adapt the shared test client to sign in; rewrite the tests that asserted guest access.

### Task 2: Gmail transport
**Files:** create `app/services/mail_gmail.py`; modify `app/services/mail.py`, `app/config.py`, `.env.example`; test `tests/test_mail_gmail.py`; ADR-030.
**Produces:** `GmailApiTransport(sender, client_id, client_secret, refresh_token, web_base_url, opener, executor)`; `MAIL_TRANSPORT=disabled|gmail_api`.
- [ ] Test: token is only in the URL fragment, never logged; send is dispatched off the request thread; production refuses incomplete configuration.

### Task 3: Synthetic demo account
**Files:** create `app/services/demo_account.py`, `scripts/demo_account.py`, `docs/DEMO_GUIDE.md`; modify `app/services/accounts.py`; test `tests/test_demo_account.py`.
**Produces:** `DEMO_ACCOUNT_EMAIL`, `provision_demo_account(db) -> {email, password, cases}`.
- [ ] Test: refused unless demo operations are allowed; demo email cannot be registered or sign in outside demo mode; reset erases only the demo account's cases; password is generated and written only to a git-ignored file.

### Task 4: Action and resolution tracking (API)
**Files:** create `packages/kadi/kadi/resolution_tracking.py` (state machine), `app/models/kadi.py` (2 tables), `app/services/case_actions.py`, `app/api/v1/endpoints/kadi/actions.py`, `migrations/versions/0004_case_actions.py`; modify `app/services/case_purge.py`; ADR-031; `docs/api/`.
**Produces:** `GET|POST /api/v1/kadi/cases/{case_id}/actions`, `POST .../actions/{action_id}/events`, `DELETE .../actions/{action_id}`; `ALLOWED_TRANSITIONS`.
- [ ] Tests: transitions, dates, redaction of notes, evidence SHA belongs to the case, purge cascade, OpenAPI contract.

### Task 5: Web sign-in gate, action plan and tracker
**Files:** create `components/auth/RequireAccount.tsx`, `lib/actionPlan.ts`, `lib/actionPlans/*.ts`, `components/actions/{ActionPlan,ActionTracker}.tsx`; modify workspace, module views, EventSource and download links, public copy about guests.
- [ ] Tests: builders produce steps only from response fields; no "Submitted"; protected layouts use the gate.
- [ ] Mobile: sign-in screen, bearer session in SecureStore.

### Task 6: Localisation
**Files:** create `app/i18n/{t.ts,useT.ts,locales/hi.ts,locales/mr.ts,glossary.md}`, public copy `hi.ts`, `mr.ts`; modify `ShellProvider` (cookie), server pages.
- [ ] Completeness test: every `t()`/`msg()` key exists in both languages with the same placeholders.

### Task 7: Accessibility
- [ ] axe-core over every route (both themes, three languages) and a scripted keyboard walk; fix real defects; report NVDA as not tested if NVDA is unavailable.

### Task 8: Documents, gates, review
- [ ] `docs/BUSINESS_MODEL.md`, localisation, accessibility and tracking docs, `PROJECT_CONTEXT.md`, `IMPLEMENTATION_STATUS.md`.
- [ ] All gates from the directive section 17, on SQLite and PostgreSQL; security and code review of the diff.
