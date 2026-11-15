# Performance budgets (WS0)

Budgets are enforced in CI (`.github/workflows/ci.yml`). Baseline measurements and the commands used to take them
are in [`performance-baseline.md`](performance-baseline.md).

| Surface | Metric | Budget | Enforced by |
|---|---|---|---|
| Web (`apps/web`) | Initial JS per route, gzip | **170 KB**, with a ratchet for known violations (below) | `scripts/build-checks/web-bundle-budget.mjs`, `web-ci` job |
| Web `/` (mobile profile, 4x CPU, slow 4G) | Largest Contentful Paint | **Target 2000 ms** (warning). **Temporary error ceiling 2500 ms** | Lighthouse CI, `apps/web/lighthouserc.json` |
| Web `/` | Cumulative Layout Shift | **0.1** (error) | Lighthouse CI |
| Mobile (`apps/mobile`) | Android Hermes `.hbc` bundle | **2,900,000 B** | `scripts/build-checks/mobile-bundle-budget.mjs`, `mobile-ci` job |

## Web initial JS: 170 KB budget and the KNOWN_VIOLATIONS ratchet

Every route was already over 170 KB when the budget was introduced (Task 1 baseline), so a flat 170 KB gate would
fail from day one. The check instead works as a ratchet over `KNOWN_VIOLATIONS` (`{ route: ceilingKB }`):

- A route not in the map fails if it is over 170 KB (170 passes, 171 fails).
- A route in the map fails if it is over its ceiling (it cannot grow).
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
follow-up for WS4. Numbers are higher than the Task 1 baseline (`/` 253.1 KB) because the motion system was added since.

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
- `largest-contentful-paint` above 2000 ms: warning (this is the spec target).
- `largest-contentful-paint` above 2500 ms: error. **2500 ms is a temporary ceiling**, set from the 2.3 s baseline
  measurement (rounded up) because the page does not yet meet the 2000 ms target. Tighten it to 2000 ms (and delete the
  warning entry) when the WS4 bundle work lands.

`@lhci/cli` is a pinned root devDependency and bundles its own Lighthouse (13.x), so absolute numbers differ from the
Lighthouse 12.8.2 CLI used for the baseline. Compare like with like.

Local run on 2026-11-15 (lhci 0.16.1, Lighthouse 13.6): LCP 0.92-0.94 s, CLS 0.096 (3 runs). CLS is close to the 0.1 limit:
the shift comes from `ul.lp-assurances` on the landing page (the Task 1 baseline recorded CLS 0). Treat any change to the
landing page layout/motion as CLS-sensitive. The Lighthouse 12.8.2 CLI measured LCP about 4.5 s and the same CLS on that
day, on a loaded machine, so LCP is noisy across Lighthouse versions and hosts.

## Mobile bundle: 2,900,000 B

Baseline 2,319,176 B (Task 1) plus about 25% headroom, rounded to 2,900,000 B. Current size is 2,361,153 B. The headroom
exists because WS5 will import Reanimated. **After WS5, re-measure the bundle and tighten this budget**
(`MOBILE_BUNDLE_BUDGET_BYTES` in `scripts/build-checks/mobile-bundle-budget.mjs`) to the new size plus a small margin.

## Running the checks locally

Build-dependent checks live in `scripts/build-checks/`, deliberately outside `scripts/checks/` so
`npm run check:generated` (which needs no build) never runs them.

```bash
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
