# Wave 1 handoff — WS5-shell (mobile shell, real fonts, browser preview)

**Branch:** `ws5/mobile-shell` (from `wave1/integration` at a3fffaa) · **Date:** 2026-11-18 · **Status:** DONE_WITH_CONCERNS
**Design note:** `docs/superpowers/specs/2026-11-18-ws5-mobile-shell-design.md`

Nothing here was run on a device, simulator or emulator. The visual checks below are from the Expo **web** preview
in the built-in browser pane, which is not device-faithful.

## What shipped

1. **Browser preview.** `react-native-web` ~0.19.13, `react-dom` 18.3.1, `@expo/metro-runtime` ~4.0.1 (the versions
   `npx expo install` printed for SDK 52; its npm step failed with `EALLOWSCRIPTS` as expected and was finished with
   plain `npm install`; every new lockfile entry resolves from registry.npmjs.org). `app.json` gets
   `web.bundler: "metro"`. `npm run web` (existing script, `expo start --web`) serves it on :8081. The app rendered on
   web without crash before any guard; the only guard added is `tap()` skipping haptics off iOS/Android
   (`hapticsSupported`). SecureStore/FileSystem calls were already inside try/catch and are not reached by the shell.
   The source map of the Android export contains no `react-native-web`, `react-dom` or `@expo/metro-runtime` module.
2. **Shell.** `App.tsx`: themed `StatusBar`, token-built React Navigation theme (`navigationTheme`), explicit insets
   instead of a global `SafeAreaView`, offline banner moved under the header. `Header`: top inset, brand in Fraunces,
   BYOD marker, EN/HI/MR segmented control (44x44 targets, radio semantics) and theme toggle, all motion Pressables.
   `TabBar` (custom `tabBar`): motion Pressable per tab, `role=tab` + selected state (also `aria-selected` because
   react-native-web 0.19 does not map `accessibilityState.selected`), sliding pill (`SlidingIndicator`), bottom inset,
   tabPress/tabLongPress semantics. Tab transition `shift` / stack `slide_from_bottom`, both `none` under reduced
   motion, token durations. `Button` (TouchableOpacity -> motion Pressable, Inter 600 label) and `Card` (Reveal on mount
   by default, optional `onPress`) on the motion system. New primitives `Skeleton`/`SkeletonText`/`SkeletonCard`
   (motion `Pulse`) and `EmptyState`. Pure logic in `src/shell/logic.ts`.
3. **Real fonts.** `src/theme/fontFamily.ts`: `fontFamily(role, weight)`, `font()`, `textStyles` map to the exact Expo
   family names (nearest loaded weight, ties heavier); a test keeps it in sync with `useAppFonts` imports. Used by
   header, tab bar, Button, EmptyState and the navigation theme. Screen text still uses system fonts (redesigned per
   screen later).
4. **Deferred WS0 fixes, each tested.** `useAppFonts` timeout (`FONT_LOAD_TIMEOUT_MS` = 6000, pure `fontGate`) so the
   splash cannot hang; load error/timeout logged via `devWarn` (only in `__DEV__`, `src/logging.ts`), no raw
   `console.warn`. `Pressable` appends its press scale to a caller `transform` (`splitTransform` + `withPressScale`).
   `Reveal` animates at most once and a late reduce-motion prime does not replay it (`revealAction`). `App.tsx` clears
   the prime timer when the prime settles.

## Decision taken during implementation (needs a ruling): motion on RN `Animated`, not Reanimated

Android export (`EXPO_NO_TELEMETRY=1 npx expo export --platform android`, Hermes `.hbc`, plain export without
`--source-maps`), budget check `npm run check:mobile-budget -- <dir>`:

| State | Bytes | Modules | Budget check |
|---|---|---|---|
| Before (a3fffaa) | 2,361,153 | 909 | PASS |
| Shell on Reanimated-based `src/motion` (commit 02881ad) | 3,146,268 | 1,100 | **FAIL**, over by 246,268 B |
| Shell on RN `Animated`-based `src/motion` (shipped, 2007211) | 2,394,806 | 929 | PASS (505,194 B margin) |

Reanimated was 172 modules / about +785 KB, more than the headroom, and the budget may not be raised without a
documented ruling. So `Reveal`, `Pressable`, `SlidingIndicator`, `Pulse` and `Parallax` keep their props and
reduced-motion rules but use the built-in `Animated` API (opacity/transform only, native driver on device, JS on
web). No app code imports `react-native-reanimated` (test-enforced); the package stays installed. `Parallax` now takes
an `Animated.Value` (it had no callers). This deviates from the foundation spec line "Mobile: Reanimated 3"; the
integrator/user should rule: keep `Animated` (then tighten the budget to about 2.5 MB) or raise the budget to about
3.2 MB and revert 2007211. The budget constant was deliberately **not** changed. `react-native-gesture-handler` is
still not imported.

## Test evidence (run in the worktree)

- `apps/mobile`: `npm run type-check` clean; `npm test` **182/182 pass** (baseline 156; +26 in `tests/shell.test.ts`).
- Root: `npm run check:generated` 3/3 PASS; `npm test` 61/61 pass.
- `check:mobile-budget` against the final export: 2,394,806 B, PASS.

## Browser preview: what was actually seen (375x812, Expo web, dark and light)

- Header: "ArogyaRakshak" in Fraunces with a green "BYOD" line under it, EN/HI/MR segmented control (active segment
  forest green), sun/moon toggle; all fit at 375 px. Measured targets: segments 44x44 after a fix (they were 40x44),
  tabs 63x56.
- Tab bar: six emoji+label tabs; all labels fit after reducing the tab label to 10 px (SchemeSetu/DawaCheck were
  truncated at 11 px). A rounded pill sits behind the active tab; clicking SchemeSetu, DawaCheck and BimaNyay moved
  it and switched screens; `aria-selected` true on the active tab. The pill's transform passed through intermediate
  values (4 -> 39 -> 191.5 for BimaNyay), so it animates; frame timing could not be measured because the pane renders
  about one frame while a script is evaluated.
- Dark and light: switching the emulated colour scheme re-themed header, tab bar, cards and buttons live; no white
  flash areas seen.
- Hindi: pressing HI changed the header title to "आरोग्यरक्षक" (system Devanagari fallback; Fraunces has no Devanagari).
  Tab labels and screens stayed English — pre-existing, see follow-ups.
- Fonts: `document.fonts` showed `Inter_500/600/700`, `Fraunces_600SemiBold`, `JetBrainsMono_700Bold` loaded and the
  tab labels computed to `Inter_600SemiBold`.
- Offline banner: shown while `localhost:8000/health` refused connections; hidden later when some other process on
  the machine (not started by this stream) began answering 200. Console errors were only those refused `/health`
  calls; the only non-Metro request was that `/health` call.
- Reduced motion was not emulated (the code path is unit-tested only).

## Not verified

- Anything on a device/emulator: native driver animations, haptics, real fonts on Android/iOS, safe-area insets on
  notched devices, status bar colour, tab/stack transitions on native, splash timeout behaviour.
- Reduced-motion rendering in the preview; Skeleton/EmptyState are not used by any screen yet, so they were not seen.
- CI on GitHub.

## Follow-ups

- **Ruling on Reanimated vs budget** (above), then set `MOBILE_BUNDLE_BUDGET_BYTES`.
- **Language state is per component** (`useLanguage` keeps local `useState`), so the header switch only re-renders the
  header; tabs and screens stay in English. Needs a shared language store/context (touches every screen's copy).
- CameraScan (`fullScreenModal`) still opens below the app header, as before (header lives outside the navigator).
- Tab icons are emoji (not tintable); an icon set would cost bundle size.
- Header title in Hindi/Marathi falls back to the system face; a Devanagari display face is not bundled.
- `Card` reveals on mount by default; if a screen puts Cards in a virtualised list, pass `reveal={false}` there.
- Pre-existing: `expo-doctor` expects react-native 0.76.9 (0.76.7 installed); `useOfflineStorage` still has a raw
  `console.warn` (not shell code, untouched).

## Local-only artefacts (not committed)

`.claude/launch.json` in the worktree (gitignored; the preview tool reads the main checkout's config, so the server
was started from the worktree with `npx expo start --web --port 8081` and opened by URL). Exports were written to the
session scratchpad. All dev servers started by this stream were stopped.
