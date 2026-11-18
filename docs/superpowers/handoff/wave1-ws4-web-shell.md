# Wave 1 handoff — WS4-shell (web shell, performance, CLS)

**Branch:** `ws4/web-shell` (from `wave1/integration` @ a3fffaa) · **Date:** 2026-11-18 · **Design note:**
`docs/superpowers/specs/2026-11-18-ws4-web-shell-design.md`. Includes the fixes from the first review round.
Environment for every number below: Windows 11, Node 24.19.0, Next.js 16.4.2 (Turbopack), local Chrome.

## What shipped

**Shell (root layout, every route incl. 404 and the error boundary)** — `apps/web/app/shell/`
- `SkipLink` (first focusable, localized), `SiteHeader`, one `<main id="main-content" tabIndex=-1>`, `SiteFooter`.
  Pages render content only; the old per-page `Header.tsx`/`Footer.tsx` are deleted. `global-error` keeps its own
  frame (`StatusPage standalone`).
- Header: brand, nav at ≥1024 px anchored to the brand (`aria-current="page"`), EN/हिंदी/मराठी switch
  (`aria-pressed`, `lang` per label), theme toggle, menu button. Fixed height. `data-elevated` after 8 px; below 1024 px
  `data-hidden` (transform) on scroll down past 120 px, back on scroll up; never under reduced motion, with the drawer
  open or focus inside (`headerScroll.ts`, unit-tested).
- Header slot for page chips (demo pill, signed-in reviewer): **out of flow**, hanging below the header row's right
  content edge (phones: pill under the emblem). The signed-in chip shows in the header only from 1440 px (it is on
  the profile card too).
- Drawer (`MobileNav`): native modal `<dialog>` (nav, five checks as `/#module-<id>` links, language switch, BYOD
  note); slide-in only under `prefers-reduced-motion: no-preference`; scroll lock with `html { scrollbar-gutter:
  stable }` (no effect on overlay-scrollbar platforms such as most phones and default macOS); closes when the viewport
  grows past the compact breakpoint (`drawerShouldClose`).
- `ShellProvider`: in-memory language shared across routes, mirrored to `<html lang>`; three contexts so the slot
  never re-renders pages.
- Route transitions: `TransitionLink` (real `<a>`, prefetch on hover/focus/touch) → `navigateWithTransition`, which
  hands the navigation promise to `startViewTransition`. The wait resolves on pathname commit and is **capped at
  400 ms** (`ROUTE_COMMIT_TIMEOUT_MS`); links to the **same pathname** (search/hash only) never start a transition;
  skipped under reduced motion, without support and in hidden documents. Fake-timer tests.
- `shellCopy.ts`: shell strings in 3 languages (tagline, BYOD, tabs, footer moved verbatim from `translations.ts`,
  which reuses them). **New hi/mr strings are flagged `NEEDS NATIVE-SPEAKER QA`.**
- `ModuleTabs`: WAI-ARIA tabs keyboard model, SVG icons instead of emoji, selection mirrored to `#module-<id>`; the
  home page opens a check from the hash on load (instant) and on `hashchange`.
- `PageContainer` / `PageSection`; `LazyPanel` (sized `aria-busy` placeholder for every `next/dynamic`); safe-area
  handling (`viewport-fit=cover`; `scroll-padding-top` includes `env(safe-area-inset-top)`); 44 px targets for
  language buttons and footer links; focus-visible rings.
- Static `public/manifest.webmanifest` with SVG `any` + `maskable` icons. **Web app manifest present; installability
  not verified** (SVG-only icons, no PNG 192/512, no apple-touch-icon). **No service worker.**

## Performance (initial JS per route, gzip KB, `node scripts/measure-baseline.mjs apps/web/.next`)

| Route | Start (a3fffaa) | Final | Ceiling |
|---|---|---|---|
| `/` | 254.24 | 222.26 | 223 (was 255) |
| `/clinical-review` | 201.87 | 190.32 | 191 (was 203) |
| `/motion-lab` | 230.63 | not built for production | removed (was 231) |
| `/_not-found` | 182.79 | 179.84 | 180 (was 184) |
| `/_global-error` | 174.57 | 171.94 | 172 (was 175) |

**Design-note targets missed:** `/` ≤ 215 (final 222.26) and `/clinical-review` ≤ 190 (final 190.32).
How: off-screen views via `next/dynamic`; static landing sections (hero, journey, reference coverage) as Server
Components passed into the client `HomeWorkspace`; `/motion-lab` → `page.dev.tsx`; status pages without `next/link`;
shell kept off the dictionaries. Breakdown per route (polyfills 38.70 `noModule`, React/Next runtime 128.39, layout
chunk 9.67 incl. ~6.2 for the shell, boundaries 3.08, route chunks: `/` 42.42, `/clinical-review` 10.49) is in
`docs/development/performance-budgets.md`. Next lever: load the hi/mr dictionaries on demand (Wave 3).

## Fonts and CLS
- `app/fonts.ts`: per hero family one CSS family with a preloaded **latin** face (+ next/font metric-matched local
  fallback) and an on-demand **latin-ext** face under the same name. The latin-ext face fixes a review finding:
  next/font's fallback face has no `unicode-range`, so ₹/ā/š were drawn by the local fallback. **Browser proof**
  ("₹ ā š" ×10, 32 px, role stack vs explicit Fontsource family): before sans 562.3 vs 539.9, headline 551.3 vs
  574.7, display 546.0 vs 505.2 px; after identical (539.9 / 574.7 / 505.2).
- lhci (3 runs each): **before CLS 0.0964** (`ul.lp-assurances`, "Web font loaded"), LCP ~906 ms; **final CLS 0**,
  LCP 1058–1063 ms. The LCP increase follows the latin-ext fix (Inter and Fraunces latin-ext now download for ₹);
  still under the 1500 ms warning and 2000 ms error.
- CDP probe (headless Chrome, trusted input, 375/768/1024/1280): `/` 0, `/clinical-review` 0, Hindi 0, Marathi 0
  (switch reflow only, flagged as recent input). Demo mode (status faked `demo_mode: true`): the shell/slot causes no
  shift, but the **pre-existing DemoBanner** inserted at the top of the content shifts the page: `/` 0.17 / 0.11 /
  0.08 / 0.07 and `/clinical-review` 0.16 / 0.11 / 0.08 / 0.06 (375/768/1024/1280). Demo deployments only;
  page-content follow-up for Wave 3 (demo page). Not fixed here.
- The Browser pane's tab had `requestAnimationFrame` throttled for this round (pane hidden / shared with other
  streams), so its PerformanceObserver readings were not used; the CDP probe replaced them.

## Files outside `apps/web` touched (within the plan's allowances)
- `packages/design-tokens/tokens.json` (3 font stacks) + regenerated copies, which **includes
  `apps/mobile/src/generated/tokens.ts`** (generated; re-run `npm run generate` if WS5 conflicts there); parity
  fixture updated for the 3 entries.
- `scripts/build-checks/web-bundle-budget.mjs` (ratchet down only), web sections of
  `docs/development/performance-budgets.md`. No new dependencies; no env vars.

## Verification (final run on the last commit)
Web `npm test` 232/232, lint 0, `tsc` clean, build OK; root `check:web-budget` PASS,
`check:generated` 3/3, `npm test` 61/61; lhci as above; `/motion-lab` 200 under `next dev` (curl).
Screenshots looked at (headless Chrome via CDP, final build): `/` at 375, 768 and 1280 in light and dark — header per
breakpoint as designed, server-rendered hero intact, no horizontal scroll; demo-pill placement at 375 (under the
emblem) and 1280 (below the header's right edge). Earlier in the pane (first round): drawer keyboard flow (Enter
opens, focus inside, Escape closes, focus returns), Hindi drawer rendering, `/clinical-review` and 404 frames, client
navigation. All servers started (3123 lhci, 3124 next start, 3125 next dev, headless Chrome) are stopped.

## Not verified / concerns
- Deep-link landing position and header return on scroll up in a foreground tab (pane throttled); logic is
  unit-tested; anchor offset measured once as 80 px.
- View Transition visuals; reduced motion under OS emulation; screen reader; contrast with a tool; PWA install.
- Linux CI: CLS and the local fallbacks (`local(Arial)`/`local(Times New Roman)`) unmeasured; `/_not-found` (0.16 KB)
  and `/clinical-review` (0.68 KB) headroom is small; record a Linux re-baseline if needed (documented).
- DemoBanner CLS in demo mode (above).
- New hi/mr shell strings need native-speaker review.
- Next.js upgrade notice: `next build`/`next dev` sometimes stopped with a "SecurityFatalError" text and passed on
  re-run. It comes from Next's own agent-upgrade nudge (`node_modules/next/dist/lib/upgrade/nudge.js`): Next checks
  the npm advisories endpoint and, when it judges the installed version affected, shows the nudge to a detected coding
  agent (and only offers an interactive prompt to humans on a TTY outside CI). Which advisory triggered it, and
  whether Next 16.4.2 is really affected, was not checked. No action was taken; upgrading is the user's decision.
- Out of scope / follow-ups: lazy hi/mr dictionaries, persisting the language (needs a pre-paint mechanism), old
  header/lang CSS in `globals.css` still used only by `global-error`.
