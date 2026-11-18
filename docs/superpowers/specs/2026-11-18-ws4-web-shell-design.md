# WS4-shell — Web shell design note

**Date:** 2026-11-18 · **Branch:** `ws4/web-shell` · **Plan:** `docs/superpowers/plans/2026-11-18-wave1.md` (WS4-shell)
**Scope:** `apps/web` only (plus the web budget ratchet, the web sections of `performance-budgets.md`, and token font stacks).
Page **content** is out of scope: each page is redesigned later, one page at a time (Wave 3).

## 1. Shell anatomy

The frame moves from per-page copies (each page rendered its own `<Header>`/`<Footer>`/`<main>`) into the root layout,
so every route — including 404 and the error boundary — gets the same frame and client navigations keep it mounted.

```
<html lang data-theme class=font-variables>
  <body>
    LanguageProvider (client: current language in memory, mirrors it to <html lang>)
      SkipLink            plain <a href="#main-content">, first focusable element
      SiteHeader          brand · primary nav · header slot · language switcher · theme toggle · menu button
        MobileNav         native <dialog> drawer (modal: focus trap, Esc, inert page, focus return for free)
      <main id="main-content" tabIndex=-1>  page content (pages no longer render <main>)
      SiteFooter          sources, disclaimers, nav links, language-aware
```

- **Header slot:** pages put page-specific chips (the demo pill, the signed-in reviewer) into the header through a tiny
  context (`useHeaderSlot`), so demo/clinical code stays in the routes that already ship it.
- **Primitives:** `PageContainer` and `PageSection` (no hooks, server-safe) give one max-width, gutter and vertical rhythm.
- **Module navigation:** the five checks are reachable from the header/drawer as `/#module-<id>` links; the home page reads
  the hash (on load and on `hashchange`) to open that tab and scroll to the workspace. `ModuleTabs` gets real tab keyboard
  behaviour (arrow keys, Home/End, roving tabindex, `aria-controls`) and SVG icons instead of emoji.
- **Route transitions:** `TransitionLink` (an `<a>` plus `router.push`) wraps client navigations in
  `navigateWithTransition`. The helper now passes through a promise, and the shell resolves it when the pathname changes,
  so the View Transition snapshots the new page instead of the old one (fixes the WS0 deferred minor "does not await").
  Reduced motion, unsupported browsers, modified clicks and same-page hash links fall back to normal navigation.
  `TransitionLink` replaces `next/link` in the shell, which also drops the duplicated Link module from several entry chunks.
- **PWA:** `app/manifest.ts` (served as `/manifest.webmanifest`) with SVG `any` and `maskable` icons in `public/icons/`.
  **No service worker** (offline caching of documents would contradict zero document retention).

## 2. Navigation at three breakpoints

| Width | Header shows | Drawer holds |
|---|---|---|
| < 640 px (375 test) | brand (no Devanagari/tagline/badge), theme toggle, menu button | nav, five checks, language switcher, privacy note |
| 640–1023 px (768 test) | brand + Devanagari, language switcher, theme toggle, menu button | nav, five checks, privacy note |
| ≥ 1024 px (1280 test) | brand, inline nav, language switcher, theme toggle (no menu button) | — |

**Scroll-aware:** after 8 px of scroll the header gains an elevated surface (border/shadow only; its height never changes,
so it cannot cause layout shift). Below 1024 px it slides away (transform only) when scrolling down past 120 px and returns
on any upward scroll; it never hides while the drawer is open or focus is inside it, and never hides under reduced motion.
The decision is a pure function (`nextHeaderState`) with unit tests. `scroll-padding-top` keeps anchor targets clear of it.

## 3. Performance: what becomes a dynamic import and why

Measured before (fresh build, `node scripts/measure-baseline.mjs apps/web/.next`): `/` 254.24, `/clinical-review` 201.87,
`/motion-lab` 230.63, `/_not-found` 182.79, `/_global-error` 174.57 KB gzip. About **167 KB** of every route is framework
(polyfills 38.7 + React/Next runtime 128.4), so 170 KB leaves ~3 KB for app code: the budget is not reachable without
framework changes. The goal is to cut what is ours and ratchet the ceilings down.

Rule used: split only what is **not rendered on first paint**, so the measured number is not flattered by chunks that load
during hydration anyway.
- `/`: the four inactive module views (only BillNyay renders initially); the case-desk components (stream visualizer,
  safety banner, entity review, claim pack, case timeline) that render only once a case exists; demo controls that
  render only in demo mode.
- `/clinical-review`: the three workspace tabs (they render only after sign-in).
- `/motion-lab`: a dev-only gallery that already 404s in production; it is excluded from production builds via a
  dev-only page extension (`page.dev.tsx`), so its 230 KB of client chunks are no longer shipped.
- Status pages: plain `<a>` instead of `next/link` (a full load after an error or a 404 is fine and more robust).

Verified two ways: the manifest-based measurement (what the budget check uses) and the scripts actually requested on `/`
in the browser.

## 4. CLS fix

Measured first: lhci (3 runs) CLS 0.0964, one shift on `ul.lp-assurances`, caused by "Web font loaded". Approach: load the
latin subset of the three hero families (Fraunces, Plus Jakarta Sans, Inter) with `next/font/local` straight from the woff2
files in `node_modules/@fontsource-variable/*` (no network, preloaded, `adjustFontFallback` for metric-matched local
fallbacks), and put the resulting CSS variable first in the token font stacks
(`var(--font-face-display, 'Fraunces Variable'), 'Fraunces Variable', …`). The `@fontsource-variable` imports stay for the
other subsets (latin-ext carries ₹) and for JetBrains Mono; the Devanagari fallbacks stay in every stack. Measure after with
lhci and a `PerformanceObserver('layout-shift')` run in the Browser pane. The 0.1 limit is not changed.

## 5. Budget targets

Ratchet `KNOWN_VIOLATIONS` down to the new measured values rounded up to the next whole KB; delete `/motion-lab`.
Targets: `/` ≤ 215, `/clinical-review` ≤ 190, `/_not-found` and `/_global-error` at or below today. The shell itself must
not raise `/_not-found` above its current ceiling.

## 6. Accessibility decisions

Skip link; `<main tabIndex=-1>` target; `:focus-visible` rings from `--border-focus` on every shell control; 44 px touch
targets; `aria-current="page"` on the active nav item; `aria-pressed` language buttons with `lang="hi"`/`lang="mr"` on their
labels; `<html lang>` follows the chosen language (correct Devanagari shaping and screen-reader voice); the drawer is a
modal `<dialog>` with a labelled close button; reduced motion disables the drawer slide, header hide and view transitions.
New Hindi/Marathi shell strings are stubs flagged for native-speaker review (apps/web/AGENTS.md).

## 7. Out of scope

Redesign of page content (landing, module views, reviewer workspace), lazy-loading the hi/mr dictionaries, persisting the
language choice (would need a pre-paint mechanism like the theme to avoid a flash/shift), Lenis (stays opt-in, not global).
