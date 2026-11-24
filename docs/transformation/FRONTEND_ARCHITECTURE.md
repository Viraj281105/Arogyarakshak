# ArogyaRakshak — Frontend Engineering & Component Architecture Blueprint

**Guiding Principle:** *Zero unnecessary framework migrations. Preserve Next.js 16.4.6 App Router, React 19, Vanilla CSS, `motion` 14.14.0, `lucide-react` 1.71.0, pure-SVG charts, and all working backend API contracts.*

---

## 1. Design-Token Architecture

**Single Source of Truth:** `packages/design-tokens/tokens.json` → `npm run generate` → vendored into `apps/web/app/generated/tokens.css` & `apps/mobile/src/generated/tokens.ts`.

- **Changes Required:**
  1. Replace Navy/Teal values in `tokens.json` with **Deep Forest / Warm Ivory** (`#142F2B`, `#244C42`, `#91B49C`, `#D5E7D9`, `#F4F1E8`, `#FFFFFF`, `#1D2925`, `#64766C`, `#E2E2D8`) and the 6 official semantic tokens (`#397A58`, `#52769B`, `#8066A5`, `#C28A35`, `#C4544F`, `#89918C` + ink-grade AA text variants).
  2. Flip `:root` default in `build.mjs` to **LIGHT** (`[data-theme="dark"]` for optional dark mode).
  3. Update `apps/web/app/layout.tsx` pre-paint `<script>` so default theme without stored preference is always `"light"`.
  4. Audit and remove remaining legacy hardcoded hex colors in `apps/web/app/globals.css` (~4,969 lines), splitting legacy module styles into cohesive CSS files (`billnyay.css`, `bimanyay.css`, `dawacheck.css`, `daavisetu.css`, `schemesetu.css`) and enforcing zero-drift via `tests/tokens_adoption.test.ts`.

---

## 2. Routing & Layout Architecture

### Preserved & New Routes (`apps/web/app/`)
| Route | Action | Rendering Mode | Notes |
|---|---|---|---|
| `/`, `/platform`, `/platform/[module]`, `/how-it-works`, `/security`, `/about`, `/help` | **Enhance** | Server Component (0 client copy) | Re-themed to Deep Forest / Warm Ivory + bespoke SVG illustrations |
| `/evidence-methodology`, `/trust`, `/terms` | **Add** | Server Component | Completes public transparency & legal ecosystem |
| `/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify` | **Enhance** | Client Form inside SSR Shell | 45/55 Deep Forest split layout; honest `MAIL_TRANSPORT=disabled` copy |
| `/app` (Case Desk), `/app/case`, `/app/case/[module]`, `/app/case/reports`, `/app/settings` | **Enhance** | Client Workspace (`CaseProvider`) | Case ID stays out of URL (`sessionStorage` + account cookie) |
| `/app/case/kadi`, `/app/case/evidence`, `/app/case/history` | **Add** | Client Workspace (code-split) | Elevates Kadi Documents, Evidence Explorer Graph, and Audit History into first-class surfaces |
| `/review` (+ 308 redirect from `/clinical-review`) | **Enhance** | Client Workspace (lazy tabs) | Deep Forest / Warm Ivory polish + inner panel layout refresh |

### Layout Shell Hierarchy
- `app/layout.tsx`: Root `<ShellProvider>`, `<ToastProvider>` (promote from unused primitive!), `<SiteHeader>`, `<main>`, `<SiteFooter>`, `<CommandPaletteLauncher>`.
- `app/app/layout.tsx` (New Workspace Shell): Persistent left Workspace Sidebar (`>= 1280px`), collapsible icon rail (`1024–1279px`), and Mobile Bottom 5-Tab Bar (`< 768px`) wrapping `/app/**`.
- `app/app/case/layout.tsx` (Retain & Enhance): `CaseProvider` + `CaseFrame` (Case Context bar, owned/guest badge, 90-day TTL countdown, module nav).

---

## 3. Component Audit: Retain, Enhance, Refactor, Replace, or Build New

| Component / Area | Current File(s) | Decision | Engineering Rationale |
|---|---|---|---|
| **Auth & Session Engine** | `lib/session.ts`, `hooks/useAccount.ts`, `lib/caseStore.ts`, `lib/apiFetch.ts` | **RETAIN** | Battle-tested ADR-026 cookie + guest `sessionStorage` + CSRF/Origin handling |
| **Client-Side Encryption** | `lib/packageCrypto.ts` | **RETAIN** | Verified PBKDF2 600k → AES-256-GCM (ADR-014) |
| **UI Primitives** | `components/ui/{Overlays,PageHeader,CommandPalette,DataTable,Steps,Disclosure,Toast}.tsx` | **ENHANCE & ADOPT** | Already built and unit-tested in Wave 3 M2; wire `DataTable`, `StepWizard`, `Tabs`, `ToastProvider`, and `Drawer` into production workspaces (fix `ConfirmationDialog` initial focus to Cancel) |
| **Evidence Badges** | `components/ui/Badges.tsx`, `components/public/PublicParts.tsx` | **REFACTOR** | Unify onto the 6 official semantic colour tiers mapped cleanly to all 8 backend provenance states; share static icon geometry |
| **State Panels** | `components/clinical/StatePanel.tsx` vs `components/ui/States.tsx` | **REPLACE** legacy `StatePanel` | Consolidate all 5 modules onto `ui/States.tsx` (`Loading`, `Empty`, `Error`, `PartialResult`, `InsufficientEvidence`) |
| **Chart Primitives** | `components/ui/Charts.tsx`, `dawacheck/PriceBar.tsx` | **ENHANCE & ADOPT** | Promote `BarChart`, `StackedBarChart`, `DonutChart`, `WaterfallChart`, `TimelineChart` into BillNyay, DaaviSetu, BimaNyay; add `ReasoningFlowChart` & `TrendLineChart` for SchemeSetu |
| **Evidence Graph** | `components/workspace/EvidenceGraph.tsx` | **ENHANCE** | Elevate to `/app/case/evidence` with provenance filter bar, upstream/downstream path highlight, and right-hand Provenance Inspector Drawer |
| **API Client Layer** | `app/shared/api-client/` vs `lib/apiFetch.ts` vs `hooks/useApi.ts` | **REFACTOR** | Standardize module calls onto typed `schema.d.ts` client wrappers over `apiFetch` so every endpoint (including newly wired `/icd-audit`, `/grievance`, `/eligibility/reasoning`, `/abdm/import`) is type-checked |
| **Brand & Illustrations** | `SiteHeader.tsx` inline SVG, `HeroIllustration.tsx`, `ModuleTabs.tsx` emojis | **REPLACE / NEW** | Replace generic shield & emoji tabs with `components/brand/ArogyaEmblem.tsx`, 6 custom module SVGs, and 12 tokenized botanical-scientific illustrations |
| **Fonts** | `app/fonts.ts` (Fraunces + Plus Jakarta Sans) | **REPLACE** | Switch to self-hosted `@fontsource-variable/manrope` + `@fontsource-variable/inter` + `@fontsource-variable/jetbrains-mono` |
| **Motion System** | `app/motion/*` (`motion` 14.14.0 + CSS scroll-driven) | **ENHANCE** | Keep ESLint confinement to `app/motion/**`; add `ArogyaLogoAnimated`, `ScanBeam`, and `GraphEdgeDraw` wrappers; remove unused `lenis` from default bundles |
| **Monolithic `globals.css`** | `apps/web/app/globals.css` (4,969 lines) | **REFACTOR** | Decompose into modular domain stylesheets; eliminate all non-token hardcoded hex colors |

---

## 4. Data-Binding & Newly Wired Existing Backend APIs

No new backend endpoints are required for the transformation. We wire these **already-implemented** backend routes into their redesigned module workspaces:
- **Kadi:** `POST /api/v1/kadi/cases/{id}/abdm/import` (ABDM FHIR import drawer in `/app/case/kadi`).
- **BillNyay:** `GET /api/v1/billnyay/cases/{id}/icd-audit`, `POST /api/v1/billnyay/cases/{id}/grievance`, `POST /api/v1/billnyay/outcome-estimate` (explicitly rendering `InsufficientEvidenceState`).
- **DaaviSetu:** `POST /api/v1/daavisetu/cases/{id}/claim/fill-template`, `POST /api/v1/daavisetu/claim-template/inspect`.
- **SchemeSetu:** `POST /api/v1/schemesetu/eligibility/reasoning`, `POST /api/v1/schemesetu/eligibility/trend`, `POST /api/v1/schemesetu/eligibility/transition`.

---

## 5. Mobile (`apps/mobile`) Alignment Blueprint

- Regenerate `apps/mobile/src/generated/tokens.ts` with Deep Forest / Warm Ivory Light-first tokens.
- Update `apps/mobile/src/theme/fontFamily.ts` to Manrope + Inter (+ OS Devanagari fallback).
- Complete Wave 3 M7 handoff items alongside the rebrand: Bearer session login (`session_transport: "bearer"` in `expo-secure-store`), `Authorization` header for owned-case PDF/ZIP/SSE downloads (never `?access_token=`), guest-case claiming, and optional local SLA reminders (`expo-notifications`, device-only, zero push servers).
- Keep Android bundle strictly under the **2,600,000 B** budget.
