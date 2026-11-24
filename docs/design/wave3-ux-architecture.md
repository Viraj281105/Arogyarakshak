# Wave 3 UX architecture: audit, information architecture, screen inventory, gap report

**Date:** 2026-11-23. **Status:** Milestone 1 deliverable, DRAFT, awaiting maintainer decisions (section 7).
**Input:** the maintainer's "Master UI/UX transformation" brief (2026-11-23), read against the code, `AGENTS.md`
and the ADRs. Where the brief and a project ground rule disagree, this document says so and does not resolve it
silently.

## 1. What the product actually is today (repository audit)

| Area | Fact (checked in code) | Consequence for the brief |
|---|---|---|
| Identity | **No user accounts.** ADR-008 (accepted risk) and ADR-009: access is per case via a one-time `X-Case-Access-Token`; "there is no concept of a user". The only sign-in is the clinical reviewer's (`app/clinical/auth.py`). | Login, register, onboarding, profile, family workspace and every "my ..." page have no backend. |
| Retention | ADR-003 BYOD: the uploaded file is **never persisted**, only a redacted excerpt, extracted entities and a SHA-256 digest. Cases expire after `case_ttl_days` = 90 and are purged by a server sweep (`case_retention.py`, ADR-010). | A document vault with originals, preview, download, version and access history is **forbidden** by AGENTS.md. Year-long spending analytics cannot exist. |
| Case listing | There is **no** `GET /cases` route. A client can only open a case whose id and token it holds. | A cross-case dashboard needs the client to keep its own list of cases. Mobile already holds tokens in `expo-secure-store`; web keeps the token in React state only (lost on reload). |
| Web routes | `/` (landing plus the whole case workspace in `HomeWorkspace`), `/clinical-review`, status pages. | Almost every page in the brief is new. |
| Endpoints the UI can build on | Case create/upload/stream (SSE), case insights, **case graph**, **case timeline**, resolutions, claim pack, BillNyay audit / appeal / appeal PDF / appeal verify / ICD audit / grievance / outcome estimate, DaaviSetu claim / readiness / fill-template / claim PDF / package, BimaNyay analyze / timeline, SchemeSetu eligibility / reasoning / trend / transition / income profile, DawaCheck benchmark (with and without a case), clinical review and safety governance. | The evidence graph, timeline explorer, report viewer and the module workspaces have real data behind them. |
| Insurer and government integrations | None. DaaviSetu **prepares** forms and packages; nothing is submitted to an insurer or TPA. | "Claims approved/rejected/pending" and "submitted" states would be fabricated. The brief's own rule 7 forbids them. |
| Chat / assistant | No conversational endpoint. | Universal assistant is a new backend feature. |
| Web dependencies | Next 16.4.2, React 19.2.4, `motion` 14.14.0 (Framer Motion's successor, already installed), `lenis`, fonts Inter, Fraunces, Plus Jakarta Sans, JetBrains Mono. **No chart library, no icon library.** | Motion is covered without a new dependency. Charts and icons are decisions (section 6). |
| Mobile dependencies | Expo with React Navigation (bottom tabs + native stack), `expo-camera`, `expo-secure-store`, `expo-haptics`, `expo-file-system`, FlashList. **No** `react-native-svg`, notifications or biometrics. | Lucide on mobile needs `react-native-svg` (bundle cost, measure first). Push, biometrics and local notifications are new dependencies. |
| Tokens | `packages/design-tokens/tokens.json`: forest / sage / brass palette, both themes, chart tokens. | The brief's navy / teal palette is a rebrand of this one file plus a contrast re-check. |
| Budgets | Web: the 170 KB route budget has a 167 KB floor (see the Wave 3 plan, decision 1). Mobile: 2,600,000 B. | Public pages must be Server Components (no client JS). Charts must be light. |

## 2. Brief versus ground rules

| Brief asks for | Rule it meets | Verdict |
|---|---|---|
| Document vault with originals, preview, download, version history, access history | AGENTS.md "Zero Document Retention"; ADR-003 | **Conflict. Not built.** A "Case documents" view shows what is actually kept (filename, type, digest, extracted fields, redacted excerpt) until the case expires. |
| Login, register, forgot/reset password, verify, onboarding profile, family workspace, consent per account | ADR-008 / ADR-009 (no accounts, by decision) | **Blocked by an architecture decision** (section 7, D1). |
| Dashboard: monthly/yearly spend, reimbursements, verified savings, claims approved/rejected | No accounts, 90-day expiry, no insurer integration, no verified-savings data | **Mostly not possible.** Rebuilt as a "case desk" over the cases this device holds, showing only per-case backend figures, with estimates labelled as estimates. |
| Claim "submitted" / status tracking | No insurer integration | Shown as "prepared / package ready" only. |
| Push notifications | AGENTS.md network boundary (Expo push service is a third-party host); no server-side user events | **Not built.** Local, on-device deadline reminders are possible (D5). |
| Testimonials, impact metrics | No-fabrication rule; evaluation numbers are synthetic | **Omitted.** No testimonials exist. The only metrics shown are reference-data coverage counts that come from the data files. |
| Universal assistant | No endpoint; prompt-injection exposure | **Backend gap**; proposed as a case-scoped, citation-only feature with its own ADR (Milestone 6). |
| Framer Motion | Already installed as `motion` | Allowed. |
| Geist Sans / Geist Mono | New font dependency | Use the installed Inter and JetBrains Mono instead. |
| Clinical Teal `#13A89E` as an action colour | WCAG AA | **Fails.** About 2.9:1 on white, under the 4.5:1 text minimum and the 3:1 minimum for large text and UI parts. Keep teal for fills and illustration; darken it for text and buttons (section 5). |
| Route `/platform/kadi` and the `/app/kadi` workspace | Kadi is shared infrastructure | A user-facing **Documents** surface is fine. It explains and shows Kadi's output; it is not a sixth "module". |

## 3. Information architecture (proposed)

### 3.1 Public site (no client JS beyond the shell; all buildable now)

| Route | Content source |
|---|---|
| `/` | Landing: hero, six-capability showcase, document-to-insight story, evidence-first section, privacy section, languages, FAQ excerpt |
| `/platform` | Ecosystem, Kadi shared layer, cross-module case context (consent-gated), evidence statuses |
| `/platform/{kadi,billnyay,daavisetu,bimanyay,schemesetu,dawacheck}` | Problem, workflow, inputs and outputs, a worked example labelled as synthetic, limitations, reference data and its date |
| `/how-it-works` | Upload, extract, analyse, verify, understand, act |
| `/security` | Only implemented controls: BYOD, per-case token, 90-day purge, client-side package encryption (ADR-014), redaction, no accounts (stated as a limitation) |
| `/about`, `/help` | Mission and principles; searchable FAQ, client-side over static content |

### 3.2 Workspace (case-scoped, no accounts)

| Route | What it is | Data |
|---|---|---|
| `/app` | **Case desk**: cases this browser or device holds (see D2), start a case, standalone tools | client-held list plus `GET /cases/{id}` |
| `/app/case` | Active case overview: documents kept, insights, action list, timeline, evidence graph | insights, timeline, graph, resolutions |
| `/app/case/{billnyay,daavisetu,bimanyay,schemesetu,dawacheck}` | Module workspaces for the active case | module endpoints |
| `/app/case/reports` | Report viewer for the appeal PDF, claim PDF, claim pack, verify result | existing PDF and pack routes |
| `/app/tools/{dawacheck,schemesetu,bimanyay,outcome-estimate}` | Tools that need no case | `dawacheck/benchmark`, `schemesetu/eligibility`, `bimanyay/analyze`, `billnyay/outcome-estimate` |
| `/app/settings` | Language, theme, simple language, reduced motion, read-aloud, delete case | client settings, `DELETE /cases/{id}` |
| `/review` (was `/clinical-review`, redirect kept) | Clinical reviewer workspace | clinical review routes |

The case id is **not** put in the URL; the active case is held in memory with its token. This keeps the
ADR-009 rule that a shared link must not carry access.

### 3.3 Mobile (five tabs, separate design)

**Home** (case desk), **Scan** (camera-first intake), **Cases** (cases held on the device in SecureStore),
**Tools** (the no-case tools), **Settings** (language, theme, biometrics if D5, privacy, delete). The brief's
"Records" maps to Cases, and "Profile" maps to Settings because there are no accounts.

## 4. Screen inventory

Status: **Retained** = exists, keep; **Enhanced** = exists, redesign; **New** = buildable on existing
capability; **Blocked** = needs backend work and a decision; **Not built** = conflicts with a ground rule.

| # | Brief page or feature | Status | Notes |
|---|---|---|---|
| 01 | Landing `/` | Enhanced | Split from the workspace; becomes server-rendered |
| 02 | `/platform` | New | |
| 03 | Six module pages | New | `daavisetu` spelling fixed |
| 04 | `/how-it-works` | New | |
| 05 | `/security` | New | Implemented controls only |
| 06 | `/about` | New | |
| 07 | `/help` | New | |
| 08 | Auth pages | Blocked (D1) | |
| 09–14 | Onboarding | Partly new | Welcome, preferences and walkthrough are buildable without accounts. Profile, family and per-account consent are Blocked (D1). |
| 15 | Dashboard `/app` | New, reinterpreted | Case desk; no longitudinal finance |
| 16 | My Healthcare | Blocked (D1) | Medical history would also be unverified |
| 17 | Family workspace | Blocked (D1) | |
| 18 | Document vault | Not built | Replaced by "case documents" in 21 |
| 19 | Document details | New, reduced | Extracted fields, confidence, redacted excerpt, page references; no preview or download of the original |
| 20 | Cases list | New (D2) | Client-held list |
| 21 | Case workspace | Enhanced | Overview, timeline, graph, documents kept, findings, reports |
| 22 | Universal search | New, reduced | Command palette over pages, actions and the active case's entities; no server search |
| 23 | Notifications | Not built (push) / Optional (local reminders, D5) | |
| 24 | Activity history | New | The case timeline (`/cases/{id}/timeline`) and BimaNyay timeline |
| 25 | Reports centre | New, reduced | Per-case PDFs and the claim pack; no annual summary |
| 26 | Insights `/app/insights` | Not built | No cross-case data. Per-case charts live in the module workspaces. |
| 27 | Assistant | Blocked (D4) | |
| 28 | Settings | New | |
| 29 | Support | Merged into `/help` | |
| M | Kadi workspace | New | Upload with progress, processing stages from SSE, extracted fields with confidence, corrections via the existing resolution routes |
| M | BillNyay workspace | Enhanced | Line items, findings, rate comparison, appeal, grievance, ICD audit, charts |
| M | DaaviSetu wizard | Enhanced | Readiness checks, template fill, package; ends at "package ready", never "submitted" |
| M | BimaNyay workspace and appeal studio | Enhanced | Three-column evidence view, appeal draft in en/hi/mr (localised letters exist), citation verify; draft-only |
| M | SchemeSetu workspace | Enhanced | Criterion-by-criterion evaluation from the reasoning trace; citation statuses |
| M | DawaCheck workspace | Enhanced | Search, price basis (ADR-012), comparison only when the price basis matches |
| X | Evidence graph | New | `/cases/{id}/graph` (real relationships) |
| X | Timeline explorer | New | Case timeline |
| X | Report viewer | New | |
| X | Command palette (Ctrl/Cmd+K) | New | |
| X | Side panels | New | Evidence, finding, entity details |
| X | Maps | Not built | No geographic data in the scheme rules |
| X | Calendar | Optional | Only for BimaNyay SLA deadlines that exist |
| Mob | Five-tab mobile app | Enhanced | Section 3.3 |
| Mob | Biometric unlock, offline reports, local reminders | Optional (D5) | New dependencies |
| Mob | Push notifications | Not built | |

## 5. Design system direction

- **Palette:** adopt the brief's navy / teal family in `tokens.json` (both themes), with these AA fixes, all to be
  re-measured by the existing token tests: text and button teal darkened to at least 4.5:1 on its background; Electric
  Cyan used only on dark surfaces or as a fill; evidence status colours as separate tokens (verified, provisional,
  unevaluated, insufficient evidence, AI-generated, rule-engine, user-provided, external).
- **Evidence vocabulary:** one `EvidenceBadge` with exactly those eight states, used everywhere. This is the brief's
  central rule, and it already maps to Wave 2's citation statuses (supported, scheme_only, unsupported,
  uncheckable).
- **Type:** Inter (interface), JetBrains Mono (figures, IDs, tabular numerals), Fraunces (editorial display). All
  are already installed. Indian number formatting via `Intl.NumberFormat('en-IN')` and the locale equivalents.
- **Motion:** the existing motion tokens plus `motion`; reduced-motion alternatives everywhere; figures never
  animate from zero in a way that suggests a different value (no count-up on findings).
- **Charts:** hand-built SVG primitives (bar, stacked bar, donut, waterfall, timeline, comparison) on the existing
  chart tokens, each with a data table, units, source and "estimate / verified" label. No chart library unless a
  measured need appears (D3).
- **Components:** the brief's Part 15 list, minus the account-dependent ones, built once in Milestone 2 and reused.

## 6. Dependencies (proposed)

| Package | Where | Why | Status |
|---|---|---|---|
| `lucide-react` | web | Consistent module and action icons; tree-shaken per icon | Proposed (D3) |
| `lucide-react-native` + `react-native-svg` | mobile | Same icons | Measure the bundle cost first; otherwise keep the existing glyphs |
| chart library | web | None; SVG primitives first | Not added |
| `expo-local-authentication`, `expo-notifications` (local only) | mobile | Biometric lock, deadline reminders | Only if D5 is yes |

## 7. Decisions

**Answered 2026-11-23:**
- D1: **add real accounts.** Backend milestone MA and ADR-026; the guest flow stays; no document retention.
- D2: `sessionStorage` for guest cases.
- D5: yes.
- Bundle metric: exclude `noModule` chunks.

In the inventory, rows marked "Blocked (D1)" now mean "planned after MA". See the Wave 3 plan, section 2. The
options below are kept as the record of what was weighed.

- **D1, accounts.** Keep "no accounts" (ADR-008/009) and build the case-scoped workspace above, or start a separate
  backend project for real accounts. Accounts would unlock pages 08, 09–14, 16, 17 and would need a new ADR,
  sessions, ownership checks on every route and a new threat model. **Recommendation:** keep no accounts for Wave 3.
  The privacy story is a strength of this project, and accounts are a multi-week backend change.
- **D2, case list on the web.** The web currently forgets the case on reload. Options: keep it in memory as today
  (single active case), use `sessionStorage` (per tab, same XSS exposure ADR-008 warned about for `localStorage`),
  or require re-entry of an exported case key. **Recommendation:** `sessionStorage` per tab, plus the existing
  export, with the XSS exposure written down. Mobile already uses SecureStore.
- **D3, icons and charts.** **Recommendation:** add `lucide-react` on the web; build SVG chart primitives; mobile
  icons depend on a measurement.
- **D4, assistant.** **Recommendation:** defer to Milestone 6 with an ADR. It is case-scoped, answers only from the
  case's extracted entities and computed findings with citations, never states an outcome the engines did not
  compute, and puts all case text through the existing injection guard.
- **D5, mobile extras.** Biometric lock and local deadline reminders. **Recommendation:** yes to both (new
  dependencies, device-only, no network). No push.
- **Plus the Wave 3 plan's decisions** on the bundle metric, the Next.js build flake and sign-off cadence.
