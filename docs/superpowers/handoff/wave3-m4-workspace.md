# Handoff: Wave 3 M4, workspace core and sign-in (branch `wave3/m4-workspace`)

**Date:** 2026-11-24. **Worktree:** `D:\wt\w3-m4-workspace`, branched from `wave3/integration` at `c3cb002`.
**Not touched:** `apps/api/**` (no backend change was needed), Python packages, M3's files (`app/page.tsx`,
`components/landing/**`, public routes, `components/public/**`, `shell/SiteFooter.tsx`), `PROJECT_CONTEXT.md`,
`CHANGELOG.md`. Nothing pushed.

## Routes

| Route | What | Data |
|---|---|---|
| `/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify` | Account pages (ADR-026) | `/kadi/auth/*` |
| `/app` | Case desk: start a case (upload), signed-in case list, guest cases of this tab, claim, demo controls | `GET /kadi/cases`, `GET /kadi/cases/{id}`, `POST /kadi/cases`, `POST /cases/{id}/claim` |
| `/app/case` | Open case overview: safety banner, next actions (readiness), automatic checks already run (insights), resolution questions, documents kept, timeline explorer, evidence graph | `/insights`, `/cases/{id}`, `/timeline`, `/graph`, `/resolutions`, `/safety-escalations` |
| `/app/case/{billnyay,daavisetu,bimanyay,schemesetu,dawacheck}` | The existing module views, one page each (one dynamic segment, `dynamicParams = false`). Without an open case the views show their stand-alone forms | module routes |
| `/app/case/reports` | Appeal PDF + integrity check, pre-auth PDF + claim package, Claim Pack, each with "not available for this case" | `appeal/verify` (409 = none), timeline `claim` step, downloads |
| `/app/settings` | Language, theme, simple language, read-aloud on/off, in-app reduced motion; change password; delete account; delete the open case | `/auth/password`, `DELETE /auth/me`, `DELETE /cases/{id}` |
| `/review` | Unchanged, now has its own `<title>` (via `app/review/layout.tsx`) | — |

Decision: module tabs became **routes** (`/app/case/<module>`), not tabs, so each module view is its own chunk and
the case is shared by the `/app/case` layout (`CaseProvider`). `moduleHref(id)` is now `/app/case/<id>`; old
`/app#module-<id>` links are forwarded by the desk; `/app#intake-dropzone` still lands on the upload panel.

**Public routes (M3).** `shell/nav.ts` holds the single list: `PUBLIC_PATHS` (`/platform`, `/how-it-works`,
`/security`, `/about`, `/help`) and `PLATFORM_PAGES` (`/platform/{kadi,...,dawacheck}`). Header nav: Platform,
How it works, Security, Help, My cases; drawer adds Settings, About, Reviewer; the command palette lists all of
them plus the workspace and auth pages. They match M3's final paths; at integration `PUBLIC_PATHS` can be replaced
by M3's `PUBLIC_ROUTES` import. Until merged, those links 404 on this branch.

**For M3's `/help` and `/platform` copy:** these web screens now exist: sign in, register, forgot password (says
email is not available), reset password and verify (work with a `#token=` link), case desk with "keep in my
account" (claim), settings with change password and delete account (states what is erased), per-case reports.

## Session and cookie behaviour

- All API calls go through `lib/apiFetch.ts` (the module views, clinical, demo and claim-pack fetches were moved
  onto it). Credentials: `"include"` unless the API said there is no session or could not be reached
  (`lib/session.ts`, `requestCredentials`). Reason: with the API's default wildcard `CORS_ORIGINS` the browser
  refuses every credentialed request, so a guest would break; this way guest cases keep working there and
  accounts need an explicit `CORS_ORIGINS` (as ADR-026 already requires).
- Login and the account forms always send `credentials: "include"` (the cookie must be stored).
- A 401 from a non-auth route while signed in marks the session `expired`; the header shows "Sign in", the case
  frame says the session ended (owned case) with a sign-in link (`?next=` is allow-listed to internal paths).
- SSE: guest case → `?access_token=` (ADR-009, unchanged); owned case → `new EventSource(url, { withCredentials: true })`,
  no token. A lost stream on an owned case re-checks `/auth/me`.
- Downloads (appeal PDF, claim PDF, claim package, Claim Pack) are fetched as bytes with the case header or the
  cookie, then saved; never a credential in a URL.
- **Dev:** `localhost:3000` → `localhost:8000` is the same site, so `SameSite=Strict` flows. Use `localhost`
  for both (127.0.0.1 vs localhost are different sites). `SESSION_COOKIE_SECURE=true` (`__Host-arogya_session`)
  **worked over plain `http://localhost` in the built-in Chromium browser** (verified below); Safari/other hosts
  may need `false` (development only; production refuses it).
- **Production:** `CORS_ORIGINS` (and `AUTH_TRUSTED_ORIGINS`, empty = `CORS_ORIGINS`) must list the HTTPS web
  origin; `__Host-` needs HTTPS. `docker-compose.yml` now passes `CORS_ORIGINS` (default `http://localhost:3000`),
  `AUTH_TRUSTED_ORIGINS` (empty) and `SESSION_COOKIE_SECURE` (default `true`) to the api service, with comments.

## D2: guest cases in sessionStorage

`lib/caseStore.ts`: key `arogyarakshak.guestCases.v1` (id, token, time added; max 20) and
`arogyarakshak.activeCase.v1` (id + owned flag; owned cases have no token). Per tab, gone when the tab closes; a
blocked storage falls back to memory. **Risk (accepted in D2):** any script running in the origin (XSS, a
malicious extension) can read the tokens. Mitigations: never in a URL, log or localStorage (tested); capped;
claiming moves a case to the account and its token stops working. The desk says this in the UI. The case id is
never put in a page URL. A guest case whose token is refused (403, claimed elsewhere) or gone (404) is shown as
such with "Remove from this tab".

## Other changes

- `packages/api-client`: `accounts.ts` (paths, OpenAPI types, the API's password policy `passwordProblem`, 12–128
  code points after NFKC) and a `credentials` option on `createClient`; regenerated into web and mobile.
- Header account control (`shell/AccountMenuLauncher.tsx`; the menu `AccountMenu.tsx` is fetched with `import()`
  on first open). The inline nav now starts at **1280 px** (five items overlapped the actions at 1024, measured);
  below that the drawer is used.
- Settings: in-app reduced motion (`data-motion="reduce"` set pre-paint from localStorage; `readReducedMotion`
  honours it; a global CSS rule stops animations), read-aloud on/off (`ListenSummary` hides its buttons),
  `useTheme().setTheme`.
- Copy: `components/auth/authCopy.ts` and `components/workspace/{case,desk,overview,timeline,graph,reports,settings}Copy.ts`
  (split per page area for the budget); hi/mr marked **UNREVIEWED: NEEDS NATIVE-SPEAKER QA**. The upload panel's
  strings moved verbatim to `lib/uploadCopy.ts` (translations.ts re-uses them).
- Evidence vocabulary: automatic checks = `rule-engine`; kept document excerpts = `unevaluated`; appeal integrity
  = `verified` / `insufficient-evidence`. Extracted-field confidence is shown only when the API stored one (OCR
  `min_ocr_confidence`); otherwise "Not recorded".
- Removed `HomeWorkspace.tsx` and `useCaseSession.ts`; tests that grepped them now check the new files with the
  same intent (consent sent, confirm before delete, readiness gating, code splitting). Hard-coded colours in
  `shell.css` replaced with tokens.

## Bundle sizes (gzip KB, fresh `next build`, Windows, Node 24.19.0, B1 measure)

| Route | Size | Note |
|---|---|---|
| `/app` | **166.19** | was 182.84 (ceiling 183); now under 170, so it **leaves `KNOWN_VIOLATIONS`** (map is empty) |
| `/app/case/[module]` | 166.07 | |
| `/app/case` | 165.31 | |
| `/app/settings` | 165.53 | |
| `/app/case/reports` | 163.18 | |
| `/login` / `/register` / `/forgot-password` / `/reset-password` / `/verify` | 153.37 / 153.30 / 153.06 / 153.34 / 153.32 | |
| `/review` | 156.90 | was 154.05 |
| `/` | 165.14 | was 162.23 (M3's tree will differ) |
| `/_not-found` (shell floor) | 146.24 | was 143.57: **+2.67 KB on every route** = account launcher + `/auth/me` state + icon |

Integration note: the shell's +2.67 KB adds to every route, including M3's landing; re-measure after merging.

## Verification (run 2026-11-24 on the final tree)

| Command | Result |
|---|---|
| `cd apps/web && npm run lint` | clean |
| `cd apps/web && npm test` | 271 tests, 271 pass |
| `cd apps/web && npm run build` | passed (18 static pages) |
| root `npm test` | 79 pass |
| `npm run check:generated` | 3 checks passed |
| `npm run check:web-budget` | PASS (numbers above) |
| Backend suite / `lint-imports` | not run: no `apps/api` or package change |

**End to end** (built-in browser, `next dev` on 3102 → API from this worktree on `localhost:8102` against a
throwaway Postgres 16 container, `SCHEMA_MANAGEMENT=migrate` → revision `0003_accounts`,
`CORS_ORIGINS=http://localhost:3102`, `SESSION_COOKIE_SECURE=true`, no Groq key):
register (short password refused in the browser; then the API's generic 202 text) → wrong password shows the
API's generic 401 text → sign in → `/app` "new case belongs to your account" → upload a synthetic text bill →
`/app/case` with owned badge, SSE via cookie completed, readiness, three automatic checks, documents kept with
redacted excerpt, timeline (5 steps), evidence graph (9 items, 11 links) → BillNyay page drafted an appeal →
reports showed the appeal available with integrity check; fetching the appeal PDF with the cookie returned
200 `application/pdf` (3,258 B), without it 401 → sessionStorage held only the active-case id, localStorage
nothing → reload `/app` lists the case from the server → account menu → sign out → guest case created (token in
sessionStorage, "This tab only") → sign in → "Keep in my account" → both cases listed as owned, guest token
removed → opened the claimed case with the cookie → settings: theme light, Hindi, reduce motion (attribute and
storage set) → change password → delete account ("2 case(s) … erased"), `/auth/me` 401, header back to
"Sign in" → `/reset-password#token=…` read the code and removed it from the address bar. API and web logs
contained no email address or password. `/review` title set. Console errors were only expected HTTP statuses
(401 `/auth/me` while signed out, 409 report probes).
**Responsive:** no page-level horizontal overflow at 360 px for `/app`, `/app/case`, `/app/case/reports`,
`/app/case/billnyay`, `/app/settings`, `/reset-password`, `/forgot-password` (wide tables and the case
navigation scroll inside their boxes); settings at 768 (light, Hindi) and 1280/1440 (light) looked right; header
at 1024 now uses the drawer, at 1280 the nav fits (measured 16 px to the actions). Cleanup: servers stopped,
container removed, browser tab closed.

## Not verified

- 768/1280/1440 for every route and dark/light for every route (spot checks only); 390 and 1024 widths beyond
  the header; Marathi in the browser; a screen reader; a full keyboard-only pass; reduced motion visually.
- The actual browser download dialog (the same fetch was checked in page JavaScript instead).
- Session-expiry handling in the browser (unit-tested only); the wildcard-CORS guest path in a browser.
- Safari's handling of `__Host-`/Secure on http://localhost.
- Linux CI bundle measurement; Lighthouse.
- Maintainer sign-off (plan section 4, item 8) — pending.

## Follow-ups

1. Integrator: swap `PUBLIC_PATHS` for M3's `PUBLIC_ROUTES`; re-measure budgets on the merged tree; update
   `PROJECT_CONTEXT.md`/`CHANGELOG.md`.
2. When email delivery is decided (ADR-026 open item), update `authCopy` `emailUnavailable*` and the forgot/verify
   pages; links must use `#token=` (the pages already read and strip it).
3. Native-speaker review of every hi/mr string marked UNREVIEWED; API-sourced text (timeline steps, check
   summaries, graph limitations) stays English (`lang="en"`).
4. Language choice is still in memory only (per visit), as before.
5. The `ConfirmationDialog` primitive showed the focus ring on the close button rather than Cancel in one
   screenshot; check its `autoFocus` (M2 primitive, not changed here).
6. **Mobile (M7):** use `accountPaths`/`passwordProblem` from the shared api-client; bearer login
   (`session_transport: "bearer"`), token in SecureStore, `Authorization` via `headersFor`; owned cases have
   `access_token: null`, so PDF/ZIP/SSE must use the header and save bytes (never `?access_token=`); claim flow
   for device-held guest cases.
