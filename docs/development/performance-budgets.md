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
- The `/` ceiling (255 KB, measured 254.24 KB) has under 1 KB of headroom and was measured on Windows. If the first Linux CI build differs slightly, record the Linux measurement as the new ceiling here and in `KNOWN_VIOLATIONS`; that is a re-baseline, not a widening.
- A route in the map that is now at or under 170 KB fails with "remove it from KNOWN_VIOLATIONS", so fixes stick.
- A route in the map that no longer exists in the build fails.
- A missing `.next` build, or a route without a client reference manifest, throws instead of passing.

Ceilings are the measured gzip size rounded up to the next whole KB (fresh build, 2026-11-15):

| Route | Measured (gzip KB) | Ceiling |
|---|---|---|
| `/` | 254.76 | 255 |
| `/clinical-review` | 202.39 | 203 |
| `/motion-lab` | 230.70 | 231 |
| `/_not-found` | 183.31 | 184 |
| `/_global-error` | 174.57 | 175 |

These are known violations, not accepted ones. They are shared framework + design-system + motion code; reducing them is a
follow-up for WS4. Numbers are higher than the WS0 baseline (`/` 253.1 KB) because the motion system was added since.

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

### Known issue: CLS is close to the limit (follow-up)

Local lhci run (Node 24.19.0, 3 runs): CLS 0.0964 each run, limit 0.1; the WS0 baseline recorded CLS 0. Root cause
(Lighthouse "layout shifts" / CLS culprits): `ul.lp-assurances` in the landing-page hero is pushed down once the web
fonts load (cause reported for all seven font files: "Web font loaded"). The fonts are the self-hosted `@fontsource-variable`
families added during WS0; their `@font-face` rules use `font-display: swap`, so the fallback-to-webfont swap changes the
height of the hero text above the list. Not fixed in this task because a proper fix is not small: it needs size-adjusted
fallback `@font-face` metrics for Fraunces, Plus Jakarta Sans and Inter (or `font-display: optional`/preloading), and the
font stacks come from generated design tokens. Follow-up: add metric-matched fallback fonts (or preload the hero fonts) and
confirm with lhci. The 0.1 limit is not widened. First CI runs may go red on CLS if a runner measures slightly higher.

Final reviewer's analysis: the 0.0964 was measured on Windows, where the pre-swap fallback is Segoe UI. On `ubuntu-latest` the stack falls back to DejaVu Sans, which is wider than Inter, so the font-swap shift may be larger in CI and the Lighthouse CLS step may be red. Plan: open a PR to `main`/`develop` (or run the workflow via `workflow_dispatch` on the branch) once the CI fixes are in, and read the real CI value. If it is red, fix it rather than loosen it: load the two hero families (Fraunces, Plus Jakarta Sans) through `next/font/local` pointing at the woff2 files already in `node_modules/@fontsource-variable/*` (no network) to get preload plus size-adjusted fallbacks (`adjustFontFallback`), and feed the result into the token font stack. Only if that slips, downgrade the CLS assertion to `warn` with a dated exception here that names the measured CI value, with WS4 as owner.

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
