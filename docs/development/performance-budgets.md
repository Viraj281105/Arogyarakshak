# Performance budgets (WS0)

Budgets are enforced in CI (`.github/workflows/ci.yml`). Baseline measurements and the commands used to take them
are in [`performance-baseline.md`](performance-baseline.md).

| Surface | Metric | Budget | Enforced by |
|---|---|---|---|
| Web (`apps/web`) | Initial JS per route, gzip | **170 KB**, with a ratchet for known violations (below) | `scripts/build-checks/web-bundle-budget.mjs`, `web-ci` job |
| Web `/` (mobile profile, 4x CPU, slow 4G) | Largest Contentful Paint | **2000 ms** (error; the spec target). Warning at 1500 ms | Lighthouse CI, `apps/web/lighthouserc.json` |
| Web `/` | Cumulative Layout Shift | **0.1** (error) | Lighthouse CI |
| Mobile (`apps/mobile`) | Android Hermes `.hbc` bundle | **2,900,000 B** | `scripts/build-checks/mobile-bundle-budget.mjs`, `mobile-ci` job |

## Web initial JS: 170 KB budget and the KNOWN_VIOLATIONS ratchet

Every route was already over 170 KB when the budget was introduced (WS0 baseline), so a flat 170 KB gate would
fail from day one. The check instead works as a ratchet over `KNOWN_VIOLATIONS` (`{ route: ceilingKB }`):

- A route not in the map fails if it is over 170 KB (170 passes, 171 fails).
- A route in the map fails if it is over its ceiling (it cannot grow).
- Ceilings have under 1 KB of headroom and were measured on Windows. If the first Linux CI build differs slightly, record the Linux measurement as the new ceiling here and in `KNOWN_VIOLATIONS`; that is a re-baseline, not a widening.
- A route in the map that is now at or under 170 KB fails with "remove it from KNOWN_VIOLATIONS", so fixes stick.
- A route in the map that no longer exists in the build fails.
- A missing `.next` build, or a route without a client reference manifest, throws instead of passing.

Ceilings are the measured gzip size rounded up to the next whole KB. WS4 (web shell, 2026-11-18, fresh build on
Windows, Node 24.19.0) ratcheted them down:

| Route | WS0 measured (2026-11-15) | WS4 measured (2026-11-18) | Ceiling |
|---|---|---|---|
| `/` | 254.76 | 224.85 | 225 |
| `/clinical-review` | 202.39 | 190.02 | 191 |
| `/motion-lab` | 230.70 | not built for production | removed |
| `/_not-found` | 183.31 | 179.79 | 180 |
| `/_global-error` | 174.57 | 171.94 | 172 |

What changed (details in `docs/superpowers/specs/2026-11-18-ws4-web-shell-design.md`):

- Code splitting with `next/dynamic` for what is not on screen at first paint: the four inactive module views, the
  case desk (shown once a case exists), demo controls (demo mode only) and the three reviewer-workspace tabs (after
  sign-in). BillNyay, the default tab, stays static.
- `/motion-lab` is a `page.dev.tsx` file; `next.config.ts` adds that page extension only under `next dev`.
- The 404/error pages use a plain anchor instead of `next/link` (Turbopack duplicated Link into the error,
  not-found and global-error entry chunks that every route loads).
- The new app shell (header, drawer, footer, on every route) costs about 6 KB gzip; it avoids the full page
  dictionary and the shared i18n dictionary (tests enforce this).

Why every route is still above 170 KB: about **167 KB** of each route is framework (polyfills 38.7 KB + React/Next
runtime 128.4 KB), which leaves ~3 KB for app code. The polyfill chunk is loaded with `noModule`, so modern browsers
do not download it: in the Browser pane `/` fetched 10 scripts totalling 186.1 KB compressed, which is the measured
224.85 minus the 38.7 KB polyfill chunk (and shows no lazily split chunk loads at first paint). The measurement keeps
counting polyfills (conservative). Further cuts need page-content work (Wave 3), e.g. loading the hi/mr dictionaries
on demand.

`/_not-found` has only 0.21 KB of headroom under its ceiling; if the first Linux CI build measures slightly higher,
record the Linux value as a re-baseline (as for `/` in WS0), not a widening.

### Removing a KNOWN_VIOLATIONS entry

1. Reduce the route's size to 170 KB or less and rebuild (`cd apps/web && npm run build`).
2. Run `npm run check:web-budget`. It reports "remove it from KNOWN_VIOLATIONS" for the fixed route.
3. Delete that route's line from `KNOWN_VIOLATIONS` in `scripts/build-checks/web-bundle-budget.mjs`. Never raise a ceiling to make
   CI pass; lower it when a route shrinks but is still over budget.

## Lighthouse CI (LCP, CLS)

`apps/web/lighthouserc.json` lets `lhci` start `next start` (port 3123), runs 3 times against `http://localhost:3123/` (no
external URLs), mobile form factor with the same throttling as the baseline (simulated, 4x CPU slowdown, RTT 150 ms,
1638.4 Kbps), performance category only. Aggregation is the median.

- `cumulative-layout-shift` above 0.1: error.
- `largest-contentful-paint` above 2000 ms: error (the spec target). Above 1500 ms: warning.

The 2000 ms budget is the spec target, not a loosened number. The figures in `performance-baseline.md` (LCP about 2.3 s)
came from the Lighthouse 12.8.2 CLI; this gate runs `@lhci/cli` 0.16.1, which bundles Lighthouse 13.6, and on the same
machine it measures much lower (LCP 0.92-0.94 s on 2026-11-15, for the same profile). The discrepancy between the two
tools is unexplained. If CI on a GitHub runner measures LCP above 2000 ms, investigate before loosening anything; any
loosening must be recorded here with the measured value and the reason.

**Node requirement:** `@lhci/cli` and its Lighthouse declare `engines.node >= 22.19`, so the Lighthouse step in `web-ci`
runs under Node 22 (a separate `actions/setup-node` step plus a root `npm ci` on Node 22). The rest of `web-ci` and
`foundation-checks` stay on Node 20; `foundation-checks` prints EBADENGINE warnings for `@lhci/cli`, which are accepted.
Run Lighthouse locally with Node 22.19 or newer.

`@lhci/cli` is a pinned root devDependency.

### CLS: fixed in WS4 (was 0.0964)

Before (lhci, 3 runs, 2026-11-18, unchanged WS0 build): CLS 0.0964 each run, one shift on `ul.lp-assurances`, cause
"Web font loaded". After (same config, 3 runs, with the WS4 shell): **CLS 0** each run, LCP 905–909 ms; a
`PerformanceObserver('layout-shift')` check in the Browser pane on `/` (1280 px) recorded no entries.

Fix: `apps/web/app/fonts.ts` loads the latin subset of Fraunces, Plus Jakarta Sans and Inter with `next/font/local`
from the woff2 files `@fontsource-variable/*` already installs (no network). next/font preloads them and generates
metric-matched local fallbacks (`adjustFontFallback`: Times New Roman for Fraunces, Arial for the sans families). The
token font stacks (`packages/design-tokens/tokens.json`) now start with `var(--font-face-display|headline|sans,
'<Fontsource family>')`; the Fontsource imports still serve latin-ext (the ₹ sign), the other subsets and JetBrains
Mono, and the Devanagari fallbacks are unchanged. Each hero font file is downloaded once (checked in lhci network
requests and the Browser pane).

Not verified: the GitHub `ubuntu-latest` runner. There `local(Arial)` / `local(Times New Roman)` may not resolve
(Liberation fonts may or may not be aliased), so the adjusted fallback may not apply; the preload still makes a
pre-paint swap likely. Read the first CI value; do not loosen the 0.1 limit.

## Mobile bundle: 2,900,000 B

Baseline 2,319,176 B (WS0 baseline) plus about 25% headroom, rounded to 2,900,000 B. Current size is 2,361,153 B. The headroom
exists because WS5 will import Reanimated. **After WS5, re-measure the bundle and tighten this budget**
(`MOBILE_BUNDLE_BUDGET_BYTES` in `scripts/build-checks/mobile-bundle-budget.mjs`) to the new size plus a small margin.

## Running the checks locally

Build-dependent checks live in `scripts/build-checks/`, deliberately outside `scripts/checks/` so
`npm run check:generated` (which needs no build) never runs them.

Telemetry stays off for these commands (project network rule: only Groq, the local Postgres and the PyPI/npm registries may
be contacted), which is why CI sets `NEXT_TELEMETRY_DISABLED` and `EXPO_NO_TELEMETRY` at workflow level.

```bash
export NEXT_TELEMETRY_DISABLED=1 EXPO_NO_TELEMETRY=1   # PowerShell: $env:NEXT_TELEMETRY_DISABLED='1'; $env:EXPO_NO_TELEMETRY='1'
npm ci                                   # repo root, once

# Web bundle budget (needs a fresh build; throws if .next is missing)
cd apps/web && npm run build && cd ../..
npm run check:web-budget

# Lighthouse CI (needs the build above; lhci starts and stops `next start` itself; needs Chrome)
npx lhci autorun --config=apps/web/lighthouserc.json     # output in .lighthouseci/ (gitignored)

# Mobile bundle budget
cd apps/mobile && npx expo export --platform android --output-dir /tmp/mobile-export && cd ../..
npm run check:mobile-budget -- /tmp/mobile-export

# Pure budget logic + everything else under root tooling
npm test
```
