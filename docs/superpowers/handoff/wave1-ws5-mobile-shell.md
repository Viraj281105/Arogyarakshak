# Wave 1 handoff — WS5-shell (mobile shell, real fonts, browser preview)

**Branch:** `ws5/mobile-shell` (from `wave1/integration` at a3fffaa) · **Date:** 2026-11-18 · **Status:** DONE (review round applied; device verification outstanding)
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

## Review round (2026-11-18): rulings applied and findings fixed

- Ruling 1: the motion system stays on React Native `Animated` (native driver); Reanimated stays out.
- Ruling 2: `MOBILE_BUNDLE_BUDGET_BYTES` 2,900,000 -> **2,600,000** (script, `scripts/tests/budgets.test.mjs`,
  `performance-budgets.md`).
- Ruling 3: `react-native-reanimated` and `react-native-gesture-handler` removed from `apps/mobile/package.json` and the
  lockfile. Nothing peer-requires them (only `react-native-screens` devDependencies mention them). After removal:
  Android export succeeds, `babel.config.js` (only `babel-preset-expo`, comment updated) is fine, type-check/tests pass,
  the web preview starts. Re-adding either needs a concrete screen, a fresh measurement and a budget ruling; both
  together cost roughly +1.7 MB of JS (budget ~4.2 MB) plus native APK/AAB growth the JS budget does not capture.
- Ruling 4: foundation spec §5.4 "Mobile: Reanimated 3" line marked "Superseded 2026-11-18: RN Animated with the native
  driver; see performance-budgets.md".
- Important 1 (tab text scaling): tab icon and label `maxFontSizeMultiplier` 1.2 (`TAB_MAX_FONT_SCALE`), label
  `adjustsFontSizeToFit` (min scale 0.8) so long or Devanagari labels shrink rather than ellipsize on device, bar and row
  use `minHeight` (grow, never clip). Pure `tabContentHeight()` test: capped content fits the 56 px base. Labels stay at
  10 px: 11 px did not fit SchemeSetu/DawaCheck at 375 px.
- Important 2 (Devanagari weight): **code fix, not just documented.** `textStyleFor(preset, text, weight)` /
  `fontFor(text, role, weight)` give Devanagari text the system face plus a numeric `fontWeight` (custom family key
  removed, in one style object because react-native-web ignores a later `fontFamily: undefined`), while Latin text
  keeps the custom family without `fontWeight`, so the Android custom-family + `fontWeight` double-bold risk never
  arises. Used for the header title, tab labels and Button titles. Seen in the web preview: English title
  `Fraunces_600SemiBold` with weight 400 (no fontWeight), Hindi title system face at weight 600. Not seen on a device.
- Important 3 (Card layout): with `reveal` on, layout style keys (flex*, width/height and min/max, alignSelf, margin*,
  position and offsets, zIndex) go to the Reveal wrapper via pure `splitLayoutStyle()`; the card grows to fill a
  wrapper with a vertical size. Tested.
- Minor 4: `Reveal` tracks completion; a re-run that finds the animation interrupted snaps to the final state
  (`revealAction(started, reduced, completed)`, tested).
- Minor 5: `Parallax` memoises its `Animated.multiply` node; doc example uses `NATIVE_DRIVER`.
- Minor 7: `tests/motion.test.ts` rule updated (no reanimated import anywhere); `tests/shell.test.ts` bans
  reanimated/gesture-handler in every import form (static, side-effect, re-export, dynamic, `require`, subpaths) and as
  `package.json` dependencies.
- Minor 8: setup.md contradiction removed (5.2.1 rewritten), design-note §6 now says no `*.web.ts` files were needed,
  `accessibilityRole="header"` moved from the header container to the title text.

## Bundle (Android export, plain, `EXPO_NO_TELEMETRY=1 npx expo export --platform android`; `npm run check:mobile-budget -- <dir>`)

| State | Bytes | Modules | Budget check |
|---|---|---|---|
| Before (a3fffaa) | 2,361,153 | 909 | PASS (old 2,900,000) |
| Shell on Reanimated-based `src/motion` (02881ad) | 3,146,268 | 1,100 | FAIL vs old 2,900,000 by 246,268 B |
| Shell on RN `Animated`-based `src/motion` (2007211) | 2,394,806 | 929 | PASS |
| **Final** (review fixes, deps removed, 4605284) | **2,397,558** | 929 | **PASS vs 2,600,000** (202,442 B margin) |

## Test evidence (run in the worktree)

- `apps/mobile`: `npm run type-check` clean; `npm test` **194/194 pass** (baseline 156).
- Root: `npm run check:generated` 3/3 PASS; `npm test` 61/61 pass (includes the updated budget constant test).
- `check:mobile-budget` against the final export: 2,397,558 B, PASS vs 2,600,000.

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
- Review round re-look (375x812, after removing the deps): app starts and renders as above; all six tab labels fit
  (Home 28, BillNyay 39, DaaviSetu 49, BimaNyay 49, SchemeSetu 61, DawaCheck 58 px wide, no overflow) in
  `Inter_600SemiBold`; tab bar 65 px tall at 1x; the heading role is on the title text; HI switches the title to
  Devanagari in the system face at weight 600; dark and light both checked.

## Not verified

- Anything on a device/emulator: native driver animations, haptics, real fonts on Android/iOS, safe-area insets on
  notched devices, status bar colour, tab/stack transitions on native, splash timeout behaviour.
- Reduced-motion rendering in the preview; Skeleton/EmptyState are not used by any screen yet, so they were not seen.
- OS font scaling at 150-200% (`maxFontSizeMultiplier`, `adjustsFontSizeToFit` are native-only; the browser ignores
  them), and Devanagari weight rendering on Android/iOS.
- RTL layouts: the tab pill offset and header layout assume left-to-right; not checked (the app has no RTL language).
- CI on GitHub.

## Follow-ups

- **Language state is per component** (`useLanguage` keeps local `useState`), so the header switch only re-renders the
  header; tabs and screens stay in English. Needs a shared language store/context (touches every screen's copy).
- CameraScan (`fullScreenModal`) still opens below the app header, as before (header lives outside the navigator).
- Tab icons are emoji (not tintable); an icon set would cost bundle size.
- Header title in Hindi/Marathi uses the system face (with a real weight); a Devanagari display face is not bundled.
- Not done this round (reviewer: not required): fonts repaint after a timeout-then-late-load (Minor 9), Pressable
  press-out animating under reduced motion (Minor 10).
- `Card` reveals on mount by default; if a screen puts Cards in a virtualised list, pass `reveal={false}` there.
- Pre-existing: `expo-doctor` expects react-native 0.76.9 (0.76.7 installed); `useOfflineStorage` still has a raw
  `console.warn` (not shell code, untouched).

## Local-only artefacts (not committed)

A gitignored `.claude/launch.json` was created and later deleted (the preview tool reads the main checkout's config,
so the server was started from the worktree with `npx expo start --web --port 8081` and opened by URL). Exports were
written to the session scratchpad. All dev servers started by this stream were stopped (port 8081 free); a process on
port 8000 was not started by this stream and was left alone.
