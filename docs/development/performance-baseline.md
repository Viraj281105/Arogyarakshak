# Performance baseline (WS0)

Recorded 2026-11-15 on branch `ws0/foundation` (commit 7717ac3 plus Task 1 files). Windows 11, Node v24.19.0,
Chrome 157. These are measurements only; **no budget is set here** (budgets and the later measurements are in [`performance-budgets.md`](performance-budgets.md); note that its Lighthouse CI tool version measures LCP lower than the CLI used here, so the two LCP figures are not comparable).

## Web (apps/web, Next.js 16.4.2, Turbopack production build)

Command: `cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build`, then `node scripts/measure-baseline.mjs apps/web/.next`.

Initial JS per route = polyfills + root main files + the route's entry chunks, gzip KB. For `/` this equals
(253.10 KB) the gzip sum of the `<script src>` chunks in the prerendered `index.html`.

| Route | Initial JS (gzip KB) |
|---|---|
| `/` | 253.1 |
| `/clinical-review` | 200.88 |
| `/_not-found` | 182.55 |
| `/_global-error` | 174.34 |

### Lighthouse (home route `/`)

Command (against `npx next start -p 3123`):

```
npx lighthouse@12 http://localhost:3123/ --form-factor=mobile --screenEmulation.mobile=true \
  --throttling-method=simulate --throttling.cpuSlowdownMultiplier=4 --throttling.rttMs=150 \
  --throttling.throughputKbps=1638.4 --only-categories=performance --chrome-flags="--headless=new --no-sandbox"
```

Lighthouse 12.8.2; mobile emulation, 4x CPU slowdown, simulated slow 4G (RTT 150 ms, 1.6 Mbps down).
Three runs:

| Run | LCP (ms) | CLS |
|---|---|---|
| 1 | 2364 | 0 |
| 2 | 2330 | 0 |
| 3 | 2330 | 0 |

Baseline: LCP about 2.3 s, CLS 0. (Run 1 also: performance score 0.98, FCP 0.9 s, TBT 30 ms.)
Only `/` was measured; `/clinical-review` was not.

## Mobile (apps/mobile, Expo SDK 52, React Native 0.76.7)

Command: `cd apps/mobile && EXPO_NO_TELEMETRY=1 npx expo export --platform android --output-dir <scratchpad>`.

- Android JS bundle (Hermes bytecode, `AppEntry-*.hbc`): 2,319,176 bytes = **2264.8 KB (2.32 MB)**, 860 modules, 17 assets.
- Later measurements (same command): 2,361,153 B / 909 modules at the end of WS0 (a3fffaa); 2,394,806 B / 929 modules after
  WS5-shell (mobile shell, motion on RN `Animated`). A Reanimated-based shell measured 3,146,268 B / 1,100 modules and was
  not shipped; see `performance-budgets.md` (mobile section).

Cold start: **not measurable in CI** (needs a physical device or emulator running the app). Not measured here.
Method for later manual measurement: on a release build, `adb shell am start -W -n <package>/<activity>`
after a force-stop; record `TotalTime`. No number recorded.
