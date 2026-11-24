# Handoff: Wave 3 M2, mobile foundation (branch `wave3/m2-mobile`)

**Date:** 2026-11-24. **Worktree:** `D:\wt\w3-m2-mobile`, branched from `wave3/integration` at `7f07477` (includes
the merged M2 web foundation). **Not touched:** `apps/web/**`, `apps/api/**`, `packages/**` (tokens and api-client
included), Python packages, `PROJECT_CONTEXT.md`, `CHANGELOG.md`. Nothing pushed, no PR.

Nothing here was run on a device, simulator or emulator. The visual checks are from the Expo **web** preview in the
built-in browser pane, which is not device-faithful.

## What changed (commit order)

1. `fix(mobile)`, AA contrast. `ColorPalette` = the whole generated palette. New `src/theme/contrast.ts` (WCAG ratio,
   rgba compositing) and `src/components/ui/tones.ts`: every colour the shared components draw is a function of the
   palette there. Filled `Button` (`primary`, `danger`) uses `actionPrimary` / `statusDanger` with `textOnAction`;
   outline uses `actionPrimary`; disabled uses `textMuted` on the elevated surface. Header language segment uses the
   action pair; `OfflineBanner` the amber provisional evidence pair; legacy `Badge` lost its old `rgba()` tints.
   `tests/contrast.test.ts` checks 107 pairs per theme and bans colour literals in the shared component files.
2. `feat(mobile)`, primitives and icon map: `components/ui/` EvidenceBadge, StatusBadge, ConfidenceIndicator,
   MetricCard, Loading/Error/PartialResult/InsufficientEvidence/Offline states, BottomSheet, ConfirmationDialog,
   ToastProvider/useToast, StepWizard, Checklist, Icon; `EmptyState` extended (`action`, `children`, default glyph).
   `evidence.ts` mirrors the web vocabulary (parity test imports the web module). `src/icons/glyphs.ts` is the one
   mobile icon map (web keys + mobile five-tab keys). `tests/primitives.test.ts`.
3. `feat(mobile)`, dev-only gallery: `src/dev/PrimitivesGallery.tsx`, loaded in `App.tsx` only via
   `__DEV__ ? require(...) : null`; web preview `?gallery`, native dev menu "Primitives gallery". `ThemeProvider`
   takes an optional `forcedMode` (the gallery's Dark/Light switch).
4. `docs(wave3)`: section 7 "Mobile" appended to `docs/design/wave3-components.md`; Wave 3 M2 table and the icon
   decision added to the mobile section of `docs/development/performance-budgets.md`.
5. This handoff.

## Decisions and why

- **No SVG icons on mobile (measured).** `react-native-svg` alone was +227,700 B, with `lucide-react-native` and the
  38 icons of the map +263,305 B, putting the bundle at 2,662,807 B (budget 2,600,000). Glyph map instead; a test
  keeps both packages out of `package.json` until a budget ruling. Both were installed only for the measurement and
  uninstalled; `package.json` and the lockfile are unchanged.
- **No gesture library.** BottomSheet/Dialog use RN `Modal` + `Animated` (native driver); close by button, scrim tap
  or Android back. No swipe-to-dismiss (that would need Gesture Handler, ~934 KB, or a PanResponder; left for M7/M8
  if a screen needs it).
- **Danger fill keeps `statusDanger`** with `textOnAction` (navy in dark, 7.11:1; white in light, 6.54:1).
- **Colours only through `tones.ts`.** That is what makes the contrast test cover "every pairing the shared components
  use" rather than a hand-kept list.
- **Primitives are not re-exported from `components/index.ts`**, so screens that import the barrel do not pull them
  into the bundle until they use them (`import ... from '../components/ui'`).

## Measured numbers

Bundle (`EXPO_NO_TELEMETRY=1 npx expo export --platform android`, plain, `npm run check:mobile-budget -- <dir>`):

| State | Bytes | Budget check |
|---|---|---|
| Before (7f07477) | 2,399,502 | PASS |
| + react-native-svg only (probe) | 2,627,202 | FAIL by 27,202 |
| + react-native-svg + lucide-react-native, 38 icons (probe) | 2,662,807 | FAIL by 62,807 |
| **Final** | **2,416,556** | **PASS** (183,444 B margin) |
| Final + all `components/ui` imported in production (probe) | 2,452,640 | PASS (147,360 B margin) |

The gallery strings ("Primitives (dev only)", "Primitives gallery") are absent from the final `.hbc`.

Contrast (107 pairs per theme, 0 failures): primary button label 6.36 light / 7.67 dark; danger 6.54 / 7.11;
offline banner 6.10 / 7.15; lowest text pair 4.61 / 5.07 (disabled label); lowest evidence label 5.04 / 6.08.
Before: white on dark `brandCyan` 2.04, white on dark `statusDanger` 2.44, black on light `statusWarning` 3.74. The test
also caught the upcoming-step ring (1.5-1.8:1) and sheet handle (2.0-2.5:1) before they shipped; both use `textMuted`.

## Verification (run 2026-11-24 on the final tree)

| Command | Result |
|---|---|
| `cd apps/mobile && npm run type-check` | clean |
| `cd apps/mobile && npm test` | 215 tests, 215 pass (was 194) |
| root `npm test` | 75 tests, 75 pass |
| `npm run check:generated` | 3 checks passed |
| `npm run check:mobile-budget -- <export>` | PASS, 2,416,556 B |

`apps/mobile` tests print `[caseAuth] ... TransformError` lines from existing tests (react-native imported under
tsx); they were there before this branch and the tests pass.

**Web preview (built-in browser pane, `npx expo start --web --port 8091`, no API running), not a device:**
- `/?gallery` at 360x780 dark and 390x844 light: every section rendered; filled buttons show navy text on teal (dark)
  and white on dark teal (light). `scrollWidth` = viewport width, no element past the right edge, every
  `role=button`/`radio` at least 44x44 (21 controls), at both sizes.
- BottomSheet opened, close button measured 44x44, scrim tap closed it; ConfirmationDialog ("Delete case") opened,
  Cancel closed it and the page recorded "cancelled"; overlays unmount after their close animation. Error toast shown
  with `role=alert`, `aria-live=assertive`.
- `/` at 390 light and 360 dark: header language segment on the action pair, amber offline banner (API down),
  "Capture Document" in navy on teal.
- Not seen: light theme at 360, dark at 390 (only one theme per size was viewed), the gallery's Dark/Light switch
  (the emulated system scheme was used instead), reduced motion, screen readers, Hindi/Marathi in the primitives.

## Not verified

- Anything on a device: Modal behaviour, Android back, native-driver overlay animation, live-region announcements,
  `DevSettings` menu item, glyph rendering in Android/iOS system fonts (the `⚕` reviewer glyph rendered like "$" in
  the browser's fallback font; check on device or pick another glyph), Devanagari in primitives.
- Reduced motion (code paths only: `useReducedMotion` in overlays and LoadingState, `Reveal` for toasts).
- CI on GitHub; Linux bundle measurement.

## Follow-ups for M7

1. Screens still contain ~40 colour literals (`#ef4444`, `#f59e0b`, `#22c55e`, camera styles); replace with
   `ErrorState`/`StatusBadge`/tokens when each screen is redesigned. The camera screen's white-on-black overlay was
   left alone.
2. Tab bar still uses its own emoji; switch to `MODULE_GLYPHS` / `ACTION_GLYPHS` with the five-tab IA. BillNyay is
   ⚖️ in the tab bar but 🧾 (receipt, as on web) in the map.
3. Evidence/state/toast copy is English; Hindi and Marathi need native-speaker review (same as web).
4. If a screen needs swipe-to-dismiss, measure a PanResponder version first (no new dependency).
5. `Card` still has a translucent white border literal in dark (not text; not in the contrast test).
6. No missing design token was found; nothing to ask of the web stream.

## Local-only artefacts (not committed)

Exports and temporary `App.tsx` backups are in the session scratchpad. The web preview server on port 8091 was
stopped. No `.claude/launch.json` was created.
