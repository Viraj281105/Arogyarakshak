# WS0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give web and mobile one source of truth for design tokens, API transport, shared strings and motion vocabulary, with CI-enforced performance budgets.

**Architecture:** Shared code lives in `packages/` as plain TypeScript/JSON and is **vendored** (copied, with a "GENERATED" banner) into each app by a sync script; CI fails if the copies are stale. This keeps both apps' build contexts unchanged (web's Docker context is `./apps/web`, mobile uses its own `npm ci`) and avoids npm workspaces / Metro monorepo config. UI components are never shared.

**Tech Stack:** Node 20 (`node --test`, no extra test deps), `openapi-typescript`, `@fontsource-variable/*`, `@expo-google-fonts/*`, Lenis, Motion (`LazyMotion`), Reanimated 3, Gesture Handler, FlashList, `@lhci/cli`.

**Spec:** `docs/superpowers/specs/2026-11-06-foundation-design.md`

## Deviations from the spec (flag at review)
1. Spec calls the shared pieces "packages". They are source packages under `packages/` but consumed by **vendoring**, not as installed dependencies (reason above). ADR-022 records this.
2. Spec §7 lists three ADRs. Only ADR-022 (token + shared-code pipeline) is written here; the telemetry and job-queue ADRs are written inside WS1/WS3 when those decisions are implemented.
3. Spec says "web and mobile call the backend through one typed client". WS0 delivers the client and adopts it as mobile's transport and web's status-page transport; remaining endpoints migrate page by page in WS4/WS5.
4. Spec says drop unused fonts. All four families (Fraunces, Plus Jakarta Sans, Inter, JetBrains Mono) are used today; dropping waits for the page redesigns.

## Global Constraints
- Web: Next.js 16 / React 19. Mobile: Expo 52 / RN 0.76 / React 18. Components are **not** shared.
- Keep the forest / brass / sage palette and the Fraunces + Inter look; adopting tokens must not change any computed value.
- Web initial JS ≤ 170 KB per route; LCP < 2 s and CLS < 0.1 on throttled mid-range Android; 60 fps on animated pages. Mobile numbers come from Task 1's baseline, never guesses.
- No Google Fonts requests at runtime or build time. Dependencies only from the official npm registry.
- Every animation pattern has a reduced-motion variant.
- English catalogue complete; Hindi and Marathi stubbed and flagged for human review.
- Zero document retention (ADR-003): no task stores uploaded documents.
- Web Docker build context stays `./apps/web`.
- AGENTS.md gates: after frontend changes run the dev server and verify in the browser; run `npm run lint`, `python -m pytest apps/api`, `python -m pytest packages/` before closing; update `PROJECT_CONTEXT.md` and docs.
- New dependency ⇒ update the app's `package.json` + lockfile and `docs/development/setup.md`.

## Review Focus
1. Light theme: generated CSS must reproduce every `[data-theme="light"]` override, not only dark. (Task 3, 4)
2. Hindi/Marathi (Devanagari) text must still render: Inter lacks Devanagari, so the font stacks keep a Devanagari-capable system fallback. (Task 6)
3. User flips the OS reduced-motion setting while the page/app is open: motion hooks react without reload. (Tasks 9, 10)
4. FastAPI 422 responses send `detail` as an array of `{loc,msg,type}`; the shared client must still produce a readable string, never `[object Object]`. (Task 7)
5. Network failure / timeout / aborted request yields a normalized `ApiError`, not an unhandled rejection, and case-token headers are not sent to non-case paths. (Task 7)

## Parallelism and conflict map
| Wave | Tasks | Notes |
|---|---|---|
| A | 1, 2 | Disjoint. Task 2 owns root `package.json` and `scripts/`. |
| B | 3 | Needs 2. |
| C | 4, 5, 7, 8 | Disjoint files (web CSS / mobile theme / api-client / i18n). Needs 2 (and 3 for 4, 5). |
| D | 6 → 9, 6 → 10 | 6 touches both apps' `package.json`; 9 (web) and 10 (mobile) must follow 6 and each other only per-app. |
| E | 11, 12 | 11 owns `.github/workflows/ci.yml`; no earlier task edits it. |

Each task adds its own check file under `scripts/checks/` (auto-discovered by the runner from Task 2); none edits `ci.yml`.

---

### Task 1: Performance baseline

**Files:**
- Create: `scripts/measure-baseline.mjs`, `docs/development/performance-baseline.md`

**Interfaces:**
- Produces: `docs/development/performance-baseline.md` containing numbers Tasks 11 consume: web per-route initial JS (gzip KB), web Lighthouse (LCP, CLS) on the throttled profile, mobile `expo export` JS bundle size (KB), mobile cold-start note (method + number or "not measurable in CI").

- [ ] **Step 1:** Write `scripts/measure-baseline.mjs` with `measureWebRouteSizes(nextDir: string): Record<string, number>` (gzip KB of initial JS per route from `.next` build manifests) and a CLI printing JSON.
- [ ] **Step 2:** Run `cd apps/web && npm run build`, then `node scripts/measure-baseline.mjs apps/web/.next`. Expected: JSON with a number per route.
- [ ] **Step 3:** Run `cd apps/mobile && npx expo export --platform android --output-dir <scratchpad>` and record the JS bundle size.
- [ ] **Step 4:** Run Lighthouse against `next start` on the home route with mobile emulation + 4× CPU slowdown + slow-4G; record LCP and CLS.
- [ ] **Step 5:** Write the numbers, commands and date into the baseline doc. Do not set any budget in this task.
- [ ] **Step 6:** Commit `docs: record WS0 performance baseline`.

### Task 2: Shared-code tooling and ADR-022

**Files:**
- Create: `package.json` (root; scripts + devDependencies only, **no workspaces**), `scripts/sync-shared.mjs`, `scripts/run-checks.mjs`, `scripts/checks/.gitkeep`, `scripts/tests/sync-shared.test.mjs`, `docs/architecture/decisions/ADR-022-shared-code-vendoring.md`
- Modify: `.gitignore` only if root `node_modules` is not already ignored.

**Interfaces:**
- Produces: `syncShared(opts: { from: string; to: string[]; banner: string; check: boolean }): { changed: string[] }` exported from `scripts/sync-shared.mjs` (copies every file under `from` into each `to`, prepends `banner` to `.ts`/`.css`; in `check` mode writes nothing and reports files that differ or are missing). `node scripts/run-checks.mjs` runs every `scripts/checks/*.mjs` (each exports `default async function check(): Promise<void>` that throws on failure) and exits non-zero on the first failure. Root scripts: `generate`, `check:generated`, `test`.

- [ ] **Step 1:** Write `sync-shared.test.mjs`: copies files with banner; second run reports `changed: []`; `check: true` after editing a vendored file reports that file and writes nothing; missing target dir is created in write mode and reported in check mode.
- [ ] **Step 2:** Run `node --test scripts/tests/` → FAIL (module missing).
- [ ] **Step 3:** Implement `syncShared` and `run-checks.mjs`.
- [ ] **Step 4:** Run `node --test scripts/tests/` → PASS.
- [ ] **Step 5:** Write ADR-022: context (separate npm roots, web Docker context, React version split), decision (vendoring + staleness check), consequences (generated dirs are never edited by hand).
- [ ] **Step 6:** Commit `build: add shared-code vendoring tooling and ADR-022`.

### Task 3: `packages/design-tokens`

**Files:**
- Create: `packages/design-tokens/tokens.json`, `packages/design-tokens/build.mjs`, `packages/design-tokens/tests/build.test.mjs`, `packages/design-tokens/tests/fixtures/globals-vars.baseline.json`, `scripts/checks/tokens.mjs`

**Interfaces:**
- Consumes: `syncShared` is not used; this package writes two generated files directly.
- Produces: `tokens.json` shape `{ color: { dark: Record<string,string>, light: Record<string,string> }, font: Record<string,string>, space: Record<string,number>, radius: Record<string,number>, motion: { duration: Record<string,number>, easing: Record<string,string> }, z: Record<string,number> }` (keys kebab-case, no `--` prefix). `buildCss(t): string` → `:root{…dark + non-theme vars}` and `[data-theme="light"]{…light overrides}`. `buildTs(t): string` → exports `colors: { dark: Palette; light: Palette }` (keys camelCased from kebab), `spacing`, `radii`, `motion`, `fonts`. CLI `node packages/design-tokens/build.mjs [--check]` writes/checks `apps/web/app/generated/tokens.css` and `apps/mobile/src/generated/tokens.ts`.

- [ ] **Step 1:** Capture the baseline: write a one-off extraction of every custom property declared in `apps/web/app/globals.css` `:root` (line 6) and `[data-theme="light"]` (line 91) blocks into `globals-vars.baseline.json` as `{ root: Record, light: Record }`. Commit-worthy fixture; do not hand-edit.
- [ ] **Step 2:** Write `build.test.mjs`: `parity: generated :root vars equal baseline.root` and `parity: generated light vars equal baseline.light` (exact key and value equality — this pins Review Focus 1); `buildTs output camelCases keys (bg-base → bgBase)`; `--check passes when outputs are current and fails after editing a generated file`.
- [ ] **Step 3:** Run `node --test packages/design-tokens/tests/` → FAIL.
- [ ] **Step 4:** Create `tokens.json` from the baseline (colors split dark/light; `--font-display/headline/sans/mono` → `font`; spacing/radii from `apps/mobile/src/theme/spacing.ts`; motion durations/easings new: `duration.fast=150, base=250, slow=500`, `easing.standard="cubic-bezier(0.2,0,0,1)"`, `easing.emphasized="cubic-bezier(0.3,0,0,1)"`).
- [ ] **Step 5:** Implement `buildCss`, `buildTs` and the CLI; add `scripts/checks/tokens.mjs` calling the `--check` path.
- [ ] **Step 6:** Run tests → PASS; run `node packages/design-tokens/build.mjs` to emit the two generated files.
- [ ] **Step 7:** Commit `feat(tokens): add design-tokens package and generator`.

### Task 4: Web adopts generated tokens

**Files:**
- Modify: `apps/web/app/globals.css` (replace only the custom-property declarations in the `:root` and `[data-theme="light"]` blocks with `@import "./generated/tokens.css";`; keep every non-variable rule in those blocks and all component rules)
- Create: `apps/web/tests/tokens_adoption.test.ts`

**Interfaces:**
- Consumes: `apps/web/app/generated/tokens.css` (Task 3).

- [ ] **Step 1:** Write `tokens_adoption.test.ts`: `globals.css contains no hand-written custom property that tokens.css also defines`; `globals.css imports ./generated/tokens.css`; `every var(--x) used in globals.css is defined in tokens.css or globals.css`.
- [ ] **Step 2:** `cd apps/web && npm test` → new tests FAIL.
- [ ] **Step 3:** Edit `globals.css` as specified.
- [ ] **Step 4:** `npm test && npm run lint && npm run build` → PASS.
- [ ] **Step 5:** Start the dev server, open `/` in dark and light themes in the browser pane, compare `getComputedStyle(document.body)` background/colour and 5 sample variables with the baseline fixture via `javascript_tool`; capture a screenshot of each theme.
- [ ] **Step 6:** Commit `refactor(web): consume generated design tokens`.

### Task 5: Mobile adopts generated tokens

**Files:**
- Modify: `apps/mobile/src/theme/colors.ts`, `spacing.ts`, `typography.ts` (re-export values from `src/generated/tokens.ts`; keep every existing export name and the `ColorPalette` type)
- Test: `apps/mobile/tests/tokens_adoption.test.ts`

- [ ] **Step 1:** Write test: `darkColors equals generated colors.dark`; `lightColors equals generated colors.light`; `spacing.minTouchTarget is 44`; `no hex literal remains in src/theme/colors.ts`.
- [ ] **Step 2:** `cd apps/mobile && npm test` → FAIL.
- [ ] **Step 3:** Refactor the three theme files to derive from the generated module.
- [ ] **Step 4:** `npm run type-check && npm test` → PASS.
- [ ] **Step 5:** Commit `refactor(mobile): consume generated design tokens`.

### Task 6: Self-hosted fonts (web and mobile)

**Files:**
- Modify: `apps/web/app/globals.css` (delete the Google Fonts `@import` at line 3), `apps/web/app/layout.tsx`, `apps/web/package.json` + lock, `apps/mobile/package.json` + lock, `apps/mobile/App.tsx`, `packages/design-tokens/tokens.json` (font stacks), `docs/development/setup.md`
- Create: `apps/mobile/src/hooks/useAppFonts.ts`, `apps/web/tests/fonts.test.ts`, `apps/mobile/tests/fonts.test.ts`

**Interfaces:**
- Produces: `useAppFonts(): boolean` (true once fonts are loaded; `App.tsx` keeps the splash screen until true).

- [ ] **Step 1:** Write `fonts.test.ts` (web): `no fonts.googleapis.com or fonts.gstatic.com reference anywhere under app/`; `each font stack in tokens ends with a generic family`; `font stacks keep a Devanagari-capable fallback (Noto Sans Devanagari, Mangal, or system-ui)` (Review Focus 2).
- [ ] **Step 2:** Write `fonts.test.ts` (mobile): `useAppFonts source references the four bundled families and no network URL`.
- [ ] **Step 3:** Run both suites → FAIL.
- [ ] **Step 4:** Install `@fontsource-variable/{fraunces,plus-jakarta-sans,inter,jetbrains-mono}` in web and import only the latin (and latin-ext) variable stylesheets; install `expo-font`, `expo-splash-screen` and `@expo-google-fonts/{fraunces,plus-jakarta-sans,inter,jetbrains-mono}` in mobile and implement `useAppFonts`. Confirm exact stylesheet file names inside `node_modules` before importing.
- [ ] **Step 5:** Update font stacks in `tokens.json`, run `node packages/design-tokens/build.mjs`.
- [ ] **Step 6:** Run web and mobile test suites, lint, type-check, build → PASS.
- [ ] **Step 7:** In the browser pane, load `/` with the network log open; expect zero requests to Google font hosts and fonts served from the app origin. Render a Hindi and a Marathi string and confirm glyphs display (screenshot).
- [ ] **Step 8:** Commit `perf: self-host fonts, drop Google Fonts`.

### Task 7: `packages/api-client`

**Files:**
- Create: `apps/api/scripts/export_openapi.py`, `packages/api-client/openapi.json`, `packages/api-client/src/errors.ts`, `packages/api-client/src/createClient.ts`, `packages/api-client/src/index.ts`, `packages/api-client/src/generated/schema.d.ts`, `packages/api-client/tests/client.test.ts`, `scripts/checks/api-client.mjs`
- Modify: `apps/mobile/src/api/client.ts` (delegate to shared client; keep its public exports), `apps/web/app/components/StatusPage.tsx` data fetch (use shared client)
- Vendored output: `apps/web/app/shared/api-client/`, `apps/mobile/src/shared/api-client/`

**Interfaces:**
- Produces:
  - `normalizeErrorDetail(detail: unknown): string`
  - `type ApiError = { status: number; detail: string; message?: string }` (match the existing shape in `apps/mobile/src/api/types/core.ts`)
  - `createClient(o: { baseUrl: string; timeoutMs?: number; fetchImpl?: typeof fetch; headersFor?: (path: string) => Record<string, string> }): { request<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> }` — rejects only with `ApiError`.

- [ ] **Step 1:** Write `client.test.ts` with injected `fetchImpl`: `422 array detail becomes "field: msg; field: msg"` (Review Focus 4); `string detail passes through`; `object detail is JSON-stringified`; `timeout rejects with ApiError status 0 after timeoutMs`; `network failure rejects with ApiError status 0, not a TypeError` (Review Focus 5); `headersFor is called with the request path and its headers are merged`; `FormData bodies do not get a JSON content-type`; `success parses JSON; 204 returns undefined`.
- [ ] **Step 2:** Run `npx tsx --test packages/api-client/tests/` → FAIL.
- [ ] **Step 3:** Implement `errors.ts` by porting `normalizeErrorDetail` and error shaping from `apps/mobile/src/api/client.ts`, then `createClient.ts`.
- [ ] **Step 4:** Implement `export_openapi.py` (imports `app.main:app`, writes `app.openapi()` sorted, indented, trailing newline); generate `schema.d.ts` with `openapi-typescript` (root devDependency).
- [ ] **Step 5:** Add `scripts/checks/api-client.mjs`: re-export OpenAPI, regenerate types and run `syncShared` in check mode; throws with the stale file list.
- [ ] **Step 6:** Run `node scripts/run-checks.mjs` after `npm run generate` → PASS. Run `python -m pytest apps/api -q` → PASS.
- [ ] **Step 7:** Rewire mobile `request()` to the shared client with `headersFor: tokenHeaderForPath`; confirm `apps/mobile/tests/case_auth.test.ts` and `byod_and_api.test.ts` still pass and that a non-case path gets no token header (Review Focus 5).
- [ ] **Step 8:** Rewire the web status page fetch; start API + dev server and verify the status page in the browser (screenshot + `curl http://localhost:8000/health`).
- [ ] **Step 9:** Commit `feat(api-client): shared typed client generated from OpenAPI`.

### Task 8: `packages/i18n` (shared namespace)

**Files:**
- Create: `packages/i18n/src/common.ts`, `packages/i18n/src/types.ts`, `packages/i18n/tests/parity.test.ts`, `scripts/checks/i18n.mjs`
- Modify: `apps/web/app/translations.ts`, `apps/mobile/src/translations/strings.ts` (spread the shared `common` namespace into each platform dictionary)
- Vendored output: `apps/web/app/shared/i18n/`, `apps/mobile/src/shared/i18n/`

**Interfaces:**
- Produces: `type Language = "en" | "hi" | "mr"`; `type CommonStrings = { appName: string; tagline: string; byodBadge: string; byodDescription: string; tabs: Record<"billnyay"|"bimanyay"|"daavisetu"|"schemesetu"|"dawacheck", string>; … }` (final key list = intersection of keys that exist with identical meaning in both current catalogues; compute it in Step 1); `common: Record<Language, CommonStrings>`; `findMissingKeys(catalogue: Record<Language, object>): string[]`; `findUnusedKeys(catalogue, sourceFiles: string[]): string[]`.

- [ ] **Step 1:** Diff the top-level and nested keys of the two existing catalogues; write the overlap list into the top of `common.ts` as a comment and use it as `CommonStrings`.
- [ ] **Step 2:** Write `parity.test.ts`: `common has en, hi and mr`; `findMissingKeys flags a key present in en and absent in mr`; `findMissingKeys returns [] for common`; `hi and mr values that equal en are listed as UNREVIEWED_STUBS` (the test prints them, does not fail — they are the human-review list).
- [ ] **Step 3:** Run `npx tsx --test packages/i18n/tests/` → FAIL.
- [ ] **Step 4:** Implement `types.ts`, `common.ts` (move existing English plus the existing Hindi/Marathi values for those keys; no new translations invented), and the two helpers.
- [ ] **Step 5:** Spread `common` into both platform dictionaries; the existing `apps/web/tests/translations.test.ts` and mobile equivalents must pass unchanged.
- [ ] **Step 6:** Add `scripts/checks/i18n.mjs` (vendoring check + missing-key check); run web and mobile suites, lint, type-check → PASS.
- [ ] **Step 7:** Commit `feat(i18n): shared common namespace and key-parity checks`.

### Task 9: Web motion system

**Files:**
- Create: `apps/web/app/motion/{index.ts,useReducedMotion.ts,Reveal.tsx,Parallax.tsx,Magnetic.tsx,CountUp.tsx,ScrollScrub.tsx,SmoothScroll.tsx,viewTransition.ts,motion.css}`, `apps/web/app/(dev)/motion-lab/page.tsx` (404 when `NODE_ENV === "production"`), `apps/web/tests/motion.test.ts`
- Modify: `apps/web/app/layout.tsx` (mount `SmoothScroll`), `apps/web/eslint.config.mjs`, `apps/web/package.json` + lock, `docs/development/setup.md`

**Interfaces:**
- Consumes: motion tokens from `generated/tokens.css` (`--motion-duration-*`, `--motion-easing-*`).
- Produces: `useReducedMotion(): boolean` (subscribes to the `prefers-reduced-motion` media query change event); components `Reveal({ children, delay?: number })`, `Parallax({ children, speed?: number })`, `Magnetic({ children, strength?: number })`, `CountUp({ to: number, durationMs?: number, format?: (n: number) => string })`, `ScrollScrub({ children })`; `navigateWithTransition(go: () => void): void`. All render final state immediately when reduced motion is on.

- [ ] **Step 1:** Write `motion.test.ts`: `useReducedMotion updates when the media query change event fires` (Review Focus 3, with a stubbed `matchMedia`); `CountUp formats its final value synchronously under reduced motion`; `motion.css defines every animation inside a prefers-reduced-motion: no-preference block or provides a reduce override`; `no file outside app/motion imports motion, framer-motion, lenis or gsap` (source scan); `navigateWithTransition calls go() directly when document.startViewTransition is missing`.
- [ ] **Step 2:** Run `cd apps/web && npm test` → FAIL.
- [ ] **Step 3:** Install `lenis` and `motion`; implement patterns. Scroll-linked effects use CSS `animation-timeline: view()` first and fall back to a static state where unsupported; interactive pieces use `LazyMotion` with `domAnimation`.
- [ ] **Step 4:** Add ESLint `no-restricted-imports` for `motion`, `framer-motion`, `lenis`, `gsap` outside `app/motion/**`.
- [ ] **Step 5:** `npm test && npm run lint && npm run build` → PASS.
- [ ] **Step 6:** Open `/motion-lab` in the browser pane: scroll, hover, toggle emulated reduced motion; capture a performance trace and confirm no long tasks over 50 ms during scroll; confirm Lenis adds ≤ 5 KB gzip to the initial JS using `scripts/measure-baseline.mjs`.
- [ ] **Step 7:** Commit `feat(web): shared motion system with reduced-motion variants`.

### Task 10: Mobile motion system

**Files:**
- Create: `apps/mobile/babel.config.js` (Expo preset + Reanimated plugin), `apps/mobile/src/motion/{index.ts,useReducedMotion.ts,Reveal.tsx,Parallax.tsx,Pressable.tsx,CountUp.tsx,haptics.ts}`, `apps/mobile/tests/motion.test.ts`
- Modify: `apps/mobile/package.json` + lock, `docs/development/setup.md`

**Interfaces:**
- Produces: `useReducedMotion(): boolean` (initial value from `AccessibilityInfo.isReduceMotionEnabled()`, updates via the `reduceMotionChanged` event); `Reveal`, `Parallax`, `CountUp` with the same props as web; `Pressable` (scale + haptic); `tap(kind: "light" | "success" | "warning"): Promise<void>` (no-op when reduced motion).

- [ ] **Step 1:** Write `motion.test.ts` using the existing `sourceTree.ts` helper: `reanimated is imported only under src/motion`; `useReducedMotion subscribes to reduceMotionChanged and unsubscribes on cleanup` (Review Focus 3); `every exported pattern branches on useReducedMotion`.
- [ ] **Step 2:** Run `cd apps/mobile && npm test` → FAIL.
- [ ] **Step 3:** Install `react-native-reanimated`, `react-native-gesture-handler`, `@shopify/flash-list`, `expo-haptics` at the versions Expo SDK 52 pins (`npx expo install`); add `babel.config.js`; implement patterns.
- [ ] **Step 4:** `npm run type-check && npm test` → PASS; `npx expo export --platform android` succeeds and bundle size is compared with Task 1's baseline.
- [ ] **Step 5:** Run the app in Expo web/simulator if available and verify one screen using `Reveal` and `Pressable`; state plainly if no device/simulator was available and what was therefore not verified.
- [ ] **Step 6:** Commit `feat(mobile): shared motion system with reduced-motion variants`.

### Task 11: Budget gates in CI

**Files:**
- Create: `scripts/checks/web-bundle-budget.mjs`, `scripts/checks/mobile-bundle-budget.mjs`, `apps/web/lighthouserc.json`, `docs/development/performance-budgets.md`
- Modify: `.github/workflows/ci.yml` (new `foundation-checks` job running `node scripts/run-checks.mjs`; web job gains the bundle-budget and Lighthouse CI steps; mobile job gains the bundle-budget step; `CI Quality Gate` job lists the new job), root `package.json` (devDependency `@lhci/cli`)

**Interfaces:**
- Consumes: Task 1 baseline numbers and `measureWebRouteSizes`.
- Produces: web budget constant `WEB_INITIAL_JS_KB = 170` (from the spec); mobile budget = baseline bundle size + a stated headroom written in `performance-budgets.md`; Lighthouse assertions `largest-contentful-paint ≤ 2000`, `cumulative-layout-shift ≤ 0.1` on the throttled mobile profile.

- [ ] **Step 1:** Write a test in `scripts/tests/budgets.test.mjs`: `a route at 171 KB fails the web budget`; `a route at 170 KB passes`; `mobile bundle over budget fails with the size delta in the message`.
- [ ] **Step 2:** Run `node --test scripts/tests/` → FAIL, then implement the two check files.
- [ ] **Step 3:** Add `lighthouserc.json` (collect against local `next start`, no external endpoints; mobile preset; assertions above).
- [ ] **Step 4:** Edit `ci.yml` as listed; validate with `docker compose config` equivalents already in CI and a YAML parse.
- [ ] **Step 5:** Run the full check locally: `node scripts/run-checks.mjs`, web build + bundle check, `npx lhci autorun` locally. If a current route exceeds 170 KB, record it in `performance-budgets.md` as a known violation with its measured size, set that route's temporary ceiling to its baseline, and list it as a follow-up for WS4; do not hide it.
- [ ] **Step 6:** Commit `ci: enforce shared-code freshness and performance budgets`.

### Task 12: Docs and handoff

**Files:**
- Modify: `PROJECT_CONTEXT.md` (Current Work, Recent Changes, Next Tasks, Handoff), `docs/development/setup.md`, `docs/development/troubleshooting.md` (stale-generated-files failure mode and fix), `CHANGELOG.md`, `README.md` only if its structure section lists apps/packages

- [ ] **Step 1:** Update each file for what Tasks 1–11 actually delivered, including the four deviations and any budget violation recorded in Task 11.
- [ ] **Step 2:** Run the AGENTS.md checklist: `npm run lint` (web), `python -m pytest apps/api`, `python -m pytest packages/`, `curl http://localhost:8000/health`, `git diff` review, confirm no uploaded documents or stray files were left.
- [ ] **Step 3:** Commit `docs: WS0 foundation handoff`.

---

## Self-review
- **Spec coverage:** §5.1 → Tasks 3–5; §5.2 → 7; §5.3 → 8; §5.4 → 9, 10; §5.5 → 6; §6 → 1, 11; §7 → 2, 12; §10 testing → tests in every task. Gaps are listed under "Deviations".
- **Type consistency:** `Language`, `ApiError`, `useReducedMotion`, `syncShared` and `createClient` signatures are defined once (Tasks 2, 7, 8, 9, 10) and referenced by the same names.
- **Proportion:** steps give signatures, test names and commands; bodies are left to the implementer.
