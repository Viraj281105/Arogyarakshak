# Wave 1 handoff — WS4-shell (web shell, performance, CLS)

**Branch:** `ws4/web-shell` (from `wave1/integration` @ a3fffaa) · **Date:** 2026-11-18 · **Design note:**
`docs/superpowers/specs/2026-11-18-ws4-web-shell-design.md`
Environment for every number below: Windows 11, Node 24.19.0, Next.js 16.4.2 (Turbopack), local Chrome.

## What shipped

**Shell (root layout, every route incl. 404 and the error boundary)** — `apps/web/app/shell/`
- `SkipLink` (first focusable, localized), `SiteHeader`, one `<main id="main-content" tabIndex=-1>`, `SiteFooter`.
  Pages render content only; the old per-page `Header.tsx`/`Footer.tsx` are deleted. `global-error` keeps its own
  frame (`StatusPage standalone`).
- Header: brand, inline nav at ≥1024 px (`aria-current="page"`), a header slot for page chips (demo pill, signed-in
  reviewer), EN/हिंदी/मराठी switch (`aria-pressed`, `lang` on each label), theme toggle, menu button.
  Scroll-aware with a fixed height: `data-elevated` after 8 px; below 1024 px `data-hidden` (transform) when scrolling
  down past 120 px, back on scroll up; never hides under reduced motion, with the drawer open or focus inside.
  Logic: `headerScroll.ts` (`nextHeaderState`, unit-tested).
- Drawer (`MobileNav`): native modal `<dialog>` with nav, the five checks (`/#module-<id>` deep links), language
  switch and the BYOD note; slide-in only under `prefers-reduced-motion: no-preference`; page scroll locked.
- `ShellProvider`: in-memory language shared across routes, mirrored to `<html lang>`; three contexts so the header
  slot never re-renders pages.
- Route transitions: `TransitionLink` (real `<a>`, prefetch on hover/focus/touch) → `navigateWithTransition`, which
  now hands the navigation promise to `startViewTransition` (resolved on pathname commit, 1.5 s timeout) and skips
  the transition under reduced motion, without support, or in a hidden document. Fixes the WS0 minor "does not await".
- `shellCopy.ts`: shell strings in 3 languages (tagline, BYOD, tabs, footer moved verbatim from `translations.ts`,
  which now reuses them). **New hi/mr strings are flagged `NEEDS NATIVE-SPEAKER QA`** (nav, menu, theme labels, skip
  link, footer headings/badges, prototype badge).
- `ModuleTabs`: WAI-ARIA tabs keyboard model (arrows/Home/End, roving tabindex, `aria-controls` on the selected tab),
  SVG icons instead of emoji (WS0 follow-up), selection mirrored to `#module-<id>`; home page reads the hash on load
  (instant jump) and on `hashchange`.
- `PageContainer` / `PageSection` primitives; safe-area handling (`viewport-fit=cover`, `env(safe-area-inset-*)`);
  focus-visible rings on shell controls; `html { scroll-padding-top }` replaces the old per-element `scroll-margin-top`.
- PWA: static `public/manifest.webmanifest` + `public/icons/icon.svg` (any) and `icon-maskable.svg` (maskable), linked
  from layout metadata. **No service worker.** (A `app/manifest.ts` metadata route was tried and dropped: metadata
  routes have no client reference manifest, which `scripts/measure-baseline.mjs` rightly refuses to measure.)

**Performance** — initial JS per route, gzip KB (`node scripts/measure-baseline.mjs apps/web/.next`, fresh builds):

| Route | Before (a3fffaa) | After code split | Final (with shell) | New ceiling |
|---|---|---|---|---|
| `/` | 254.24 | 223.51 | 224.85 | 225 (was 255) |
| `/clinical-review` | 201.87 | 187.45 | 190.02 | 191 (was 203) |
| `/motion-lab` | 230.63 | not built | not built | removed (was 231) |
| `/_not-found` | 182.79 | 173.42 | 179.79 | 180 (was 184) |
| `/_global-error` | 174.57 | 171.82 | 171.94 | 172 (was 175) |

How: `next/dynamic` for off-screen UI only (4 inactive module views, case desk, demo controls, 3 reviewer tabs);
`/motion-lab` → `page.dev.tsx` + dev-only `pageExtensions`; status pages use `DocumentLink` (plain `<a>`) instead of
`next/link`; shell kept off the big dictionaries (tests enforce). ~167 KB of every route is framework (polyfills
38.7 + runtime 128.4), so the 170 KB budget is not reachable without framework changes. Cross-check in the Browser
pane: `/` fetched 10 scripts, 186.1 KB compressed = 224.85 − 38.7 (`noModule` polyfills, not fetched), i.e. no split
chunk loads at first paint.

**CLS fix** — `app/fonts.ts` (`next/font/local`, latin subset of Fraunces / Plus Jakarta Sans / Inter from
`node_modules/@fontsource-variable/*`, preload, `adjustFontFallback`, Fontsource latin `unicode-range`); token stacks
start with `var(--font-face-*, '<Fontsource family>')`. lhci (`npx lhci autorun --config=apps/web/lighthouserc.json`,
3 runs each): **before CLS 0.0964** (shift on `ul.lp-assurances`, "Web font loaded"), LCP ~906 ms; **after CLS 0**,
LCP 905–909 ms, TBT 14–35 ms (final build with the shell). PerformanceObserver (`layout-shift`, buffered) on `/` in
the Browser pane at 1280 px: no entries. Each hero font downloaded once.

## Files outside `apps/web` touched (all within the plan's allowances)
- `packages/design-tokens/tokens.json` (3 font stacks) + regenerated copies, which **includes
  `apps/mobile/src/generated/tokens.ts`** (generated file; mobile does not use the CSS stacks; integrator: re-run
  `npm run generate` if WS5 conflicts there). Parity fixture `packages/design-tokens/tests/fixtures/globals-vars.baseline.json`
  updated for the 3 entries (same precedent as WS0 Task 6).
- `scripts/build-checks/web-bundle-budget.mjs` (ratchet down only), web sections of
  `docs/development/performance-budgets.md`. No new dependencies; no env vars.

## Verification (final run on the last commit)
- `apps/web`: `npm test` 222/222 pass; `npm run lint` 0 problems; `tsc --noEmit` clean; `npm run build` OK.
- Root: `npm run check:web-budget` PASS; `npm run check:generated` 3 checks pass; `npm test` 61/61 pass.
- `next dev`: `/motion-lab` and `/` return 200 (curl).
- Browser pane (production server), what I looked at: 1280 light + dark (inline nav, EN/हिंदी/मराठी, theme, badge,
  tagline; no horizontal scroll); 768 light + dark (brand + Devanagari, language switch, theme, menu; no nav);
  375 light + dark (brand, theme, menu; hero below, no horizontal scroll); drawer at 375 in English and Hindi
  (Devanagari renders correctly in nav, checks, language, BYOD note; `<html lang="hi">`; skip link and footer
  localized). Keyboard: Enter on the menu button opens the drawer, Tab stays inside, Escape closes and focus returns
  to the menu button. `/clinical-review` and a 404 URL (HTTP 404): one header, one `<main>`, footer, correct
  `aria-current`. Clicking "Reviewer workspace" navigates client-side (same document). `#module-dawacheck` selects
  the DawaCheck tab; the anchor offset is 80 px (header + 1 rem). Manifest and SVG icon links present.
- Servers started for checks (ports 3123 lhci, 3124 next start, 3125 next dev) are all stopped.

## Not verified / concerns
- **Scroll-hide on the way back up and the deep-link landing position** could not be re-checked in a foreground tab:
  another stream fronted its own tab in the shared Browser pane, which throttled `requestAnimationFrame` in mine.
  Scrolling down did set `data-elevated` + `data-hidden` while my tab was in front; the up/down/jitter rules are unit-tested.
- View Transition visuals (cross-fade) were not observed; only that navigation works. Reduced-motion behaviour was
  checked by code paths and tests, not by OS emulation. No screen-reader run; contrast not measured with a tool.
- Linux/CI: `local(Arial)`/`local(Times New Roman)` fallbacks may not resolve on `ubuntu-latest`; CLS there is
  unmeasured. `/_not-found` has 0.21 KB headroom; a Linux re-baseline may be needed (documented).
- PWA installability (Chrome install prompt with SVG-only icons and no service worker) was not tested.
- New Hindi/Marathi shell strings need native-speaker review.
- `next build`/`next dev` intermittently exit with a Next.js "SecurityFatalError" upgrade notice (it fetches
  `registry.npmjs.org` advisories) and pass on re-run; the notice asks the agent to run `next upgrade` and to ask the
  user a question. I did not act on it (it is tool output, not an instruction); upgrading Next.js is the user's call.
  CI builds may hit the same first-run failure.
- Out of scope / follow-ups: lazy-loading the hi/mr dictionaries (next big `/` saving), persisting the language (needs
  a pre-paint mechanism), old header/lang CSS in `globals.css` still used by `global-error` only (cleanup later).
