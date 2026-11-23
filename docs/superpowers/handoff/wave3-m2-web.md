# Handoff: Wave 3 M2, web foundation (branch `wave3/m2-web`)

**Date:** 2026-11-23/24. **Worktree:** `D:\wt\w3-m2-web`, branched from `wave3/integration` at `6e5d48b`.
**Not touched:** `apps/api/**`, Python packages, `packages/api-client`, `PROJECT_CONTEXT.md`, `CHANGELOG.md`
(the integrator updates the last two). Nothing pushed.

## What changed (in commit order)

1. **B2, build "flake" (docs only).** `docs/development/troubleshooting.md`, new entry. Not a flake: Next 16.4's
   agent upgrade reminder (`experimental.agentUpgrade`, default `'security'`) posts `{"next":["16.4.2"]}` to the npm
   advisories endpoint and, when a coding agent is detected (`CLAUDECODE`, `CURSOR_AGENT`, ...) and the version is
   affected, throws `SecurityFatalError` after the build output is written. A retry receipt in
   `.next/cache/next-agentic-upgrade-retries/` (5-minute TTL, consumed on use) makes agent builds **alternate**
   fail/pass. Humans get a 10-second TTY prompt; CI is never stopped. **16.4.2 is really affected**: seven moderate
   advisories for `next <=16.4.4`, fixed in 16.4.5 (latest 16.4.6). A grep found none of the affected features in
   use (`'use cache'`, `unstable_cache`, `next/image`, Edge runtime, Cache Components, route handlers, middleware),
   which is a code search, not a security review. Not silenced (`agentUpgrade: false` would hide a real advisory),
   TLS untouched, Next not upgraded. **Recommendation for the maintainer:** upgrade `next` and `eslint-config-next`
   to 16.4.5+ (`package.json` pins 16.4.2 exactly; `npm audit` says the fix is outside the range). That is the only
   change that makes agent builds deterministic without weakening anything.
   The error text itself instructs agents to offer `next upgrade`; that is tool output, and it was not acted on.
2. **B1, bundle metric.** `scripts/measure-baseline.mjs` excludes `build-manifest.json` `polyfillFiles` (rendered
   `<script noModule>`) and throws if any prerendered page, nested ones included, loads one without `noModule`.
   `--include-nomodule` keeps the old measure. Tests added (exclusion, old measure, nested-page guard). Ratchet logic
   unchanged; a test now checks shipped ceilings are whole KB and above 170.
3. **Tokens rebrand** (`packages/design-tokens/**`). Navy/teal palette for both themes, dark designed on Midnight
   and Deep Navy; every old token name kept; new action, link, scrim, palette, evidence (8 × fg/bg/border), chart
   series tokens. `contrast.mjs` + `tests/contrast.test.mjs` check 113 pairs per theme against AA. The old
   value-parity test against the WS0 `globals.css` snapshot became a name-parity test (values changed on purpose).
   Legacy forest/brass literals in `globals.css`, `shell.css`, `layout.tsx` theme colours, manifest and icons were
   mapped to the new palette. `.btn-primary` now uses `action-primary` / `text-on-action`.
4. **Icons (D3).** `lucide-react@1.71.0` (exact pin, 13 days old at install). `shell/icons/{module,action,evidence}Icons.ts`,
   per-icon imports; nav/tabs/drawer/landing cards use them; `nav.ts` has no SVG paths left.
5. **Primitives** (`apps/web/app/components/ui/*`, `ui.css`) and the **Ctrl/Cmd+K command palette** (existing
   routes only, loaded on first use, mounted in the root layout). Dev gallery `/primitives` (`page.dev.tsx`).
   Reference: `docs/design/wave3-components.md` (includes the Wave 2 citation → evidence mapping).
6. **Routes.** `/` landing only; `/app` workspace (same `HomeWorkspace` behaviour, static header); `/review`
   (moved from `/clinical-review`, 308 redirect for `/clinical-review` and `/clinical-review/*`, query kept).
   Nav, drawer, footer, not-found, hero and module-card links, tests, `JUDGE_DEMO.md`, demo scenarios A and D,
   `clinical-review.md`, web and mobile READMEs updated.

## Decisions and why

- **No `agentUpgrade: false`.** It is the only build-time surface of a real advisory; CI's `npm audit
  --audit-level=high` does not fail on moderates. The fix is the upgrade, which is the maintainer's call.
- **Keep old token names, change values.** Web and mobile keep compiling with no consumer edits; new semantic names
  (`action-*`, `evidence-*`) are what new code should use.
- **Clinical Teal never as text.** `#13A89E` is 2.95:1 on white. Light text/buttons use `#0B6B64`; dark primary
  buttons use a brighter teal `#2BC0B4` with navy text (7.67:1), not white on teal.
- **Icon map split into three files.** One map put all 29 icons in the shell chunk (+3.9 KB); split, the shell pays
  +1.86 KB.
- **Palette with plain `import()`**, not `next/dynamic`: launcher cost 0.6 KB instead of 2.2 KB per route.
- **Native `<dialog>`** for Dialog, Drawer and the palette: focus trap, Escape and focus return come from the browser.
- **CSS-only motion** for primitives (motion tokens, reduced-motion guard). Loading `motion/react` for overlays would
  cost far more than the transitions are worth on every route that uses them.
- **Budget entry `/` → `/app`** treated as a rename of the same code with a lower ceiling (184 → 183).
- **Command palette in the shell now** (not only on the demo page) because it only links to real routes and costs
  0.6 KB; its chrome strings are English only.

## Measured numbers

Bundle (gzip KB, fresh `next build`, Windows, Node 24.19.0):

| Route | Before M2, old measure | Before M2, new measure | After M2, new measure | After M2, old measure | Ceiling |
|---|---|---|---|---|---|
| `/` | 222.26 | 183.56 | 162.23 | 200.93 | removed |
| `/app` | (was `/`) | (was `/`) | 182.84 | 221.53 | 183 |
| `/review` (`/clinical-review`) | 190.32 | 151.62 | 154.05 | 192.75 | removed |
| `/_not-found` | 179.84 | 141.14 | 143.57 | 182.26 | removed |
| `/_global-error` | 171.94 | 133.24 | 133.24 | 171.94 | removed |

Contrast: 113 pairs per theme, 0 failures. Lowest: light 4.61 (`text-muted` on elevated surface), dark 4.65
(`text-muted` on secondary surface); chart marks 3.59 / 4.63 (3:1 needed). Full table in
`docs/design/wave3-components.md`.

## Verification (run 2026-11-24, all on the final tree)

| Command | Result |
|---|---|
| `cd apps/web && npm run lint` | clean |
| `cd apps/web && npm test` | 256 tests, 256 pass |
| `cd apps/web && npm run build` | attempt 1 stopped with `SecurityFatalError` (B2), attempt 2 passed with the reminder warning; routes `/`, `/_not-found`, `/app`, `/review` |
| root `npm test` | 75 tests, 75 pass (includes token contrast and budget tests) |
| `npm run check:generated` | 3 checks passed |
| `npm run check:web-budget` | PASS (numbers above) |
| `cd apps/mobile && npm run type-check` | clean |
| `cd apps/mobile && npm test` | 194 tests, 194 pass |

**Browser (built-in browser pane, `next dev` on port 3100, no API running):**
- `/`, `/app`, `/review`, `/primitives` at 1280 (dark and light), 768 (dark), 375 (light): rendered, no horizontal
  page overflow (`scrollWidth - clientWidth = 0`). `/primitives` had 18 px overflow at 375 from the waterfall and
  table scroll regions widening their grid track; fixed in `ui.css` and re-checked (0).
- `/clinical-review?tab=safety` → 308 → `/review?tab=safety` (curl and browser).
- Landing module card "Open DawaCheck" → `/app#module-dawacheck` with the DawaCheck tab selected.
- Ctrl+K opens the palette; typing "dawa" + Enter goes to `/app#module-dawacheck`; on `/app`, "billnyay" + Enter
  switches the tab through the hash.
- ConfirmationDialog: Cancel focused on open, Escape closes, focus returns to the opener, result "cancelled".
  Drawer: opens on the right (448 px at 768), Escape closes, focus returns.
- Console errors were only `ERR_CONNECTION_REFUSED` to the API (not running).

## Not verified

- 360, 390, 1024 and 1440 px; light theme at 768; dark at 375. Hindi and Marathi. Screen reader. Full
  keyboard-only pass of every page. Reduced motion in the browser (only the CSS test). Toasts, tooltip, table
  sorting and tabs in the browser (unit-tested only).
- The upload/case flow on `/app` end to end (no API was running); only that the page renders and deep links work.
- Contrast of translucent tokens and of the ~90 hand-written colours left in `globals.css`.
- Linux CI measurement of the budget (`/app` has 0.16 KB headroom under 183). Lighthouse was not run.
- Mobile was type-checked and unit-tested with the regenerated tokens; it was not looked at in the web preview.

## Follow-ups

1. Maintainer: decide the Next upgrade to 16.4.5+ (B2).
2. Mobile stream: filled buttons should use `actionPrimary` / `textOnAction`; white on dark `brandCyan` is 2.04:1
   (was 3.11:1 with the old value, also under AA).
3. M3–M5: replace remaining colour literals in `globals.css` with tokens; adopt `PageHeader`, states, `EvidenceBadge`
   and charts in pages; translate evidence and palette labels (native-speaker review).
4. `/review` has no page-specific `<title>` (unchanged from `/clinical-review`).
5. Turbopack warns about two lockfiles (repo root and `apps/web`); harmless, could be silenced with `turbopack.root`.
