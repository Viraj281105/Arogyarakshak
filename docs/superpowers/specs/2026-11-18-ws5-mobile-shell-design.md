# WS5-shell — Mobile shell design note

**Date:** 2026-11-18 · **Branch:** `ws5/mobile-shell` · **Plan:** `docs/superpowers/plans/2026-11-18-wave1.md` (WS5-shell)
**Scope:** the frame every mobile screen lives in. Screen *content* (HomeScreen hero, module forms, result cards)
is redesigned later, screen by screen (Wave 3). Screen business logic and API calls do not change here.

## 1. Shell anatomy

```
SafeAreaProvider
└─ ThemeProvider
   └─ AppShell (View, bgBase)
      ├─ StatusBar          themed: light/dark content, Android background = header surface
      ├─ AppHeader          top safe-area inset, brand (Fraunces), BYOD badge, EN/HI/MR segmented control, theme toggle
      ├─ OfflineBanner
      └─ NavigationContainer (theme built from tokens: no white flash between screens)
         └─ RootNavigator (native stack: MainTabs + CameraScan modal)
            └─ BottomTabNavigator (custom AnimatedTabBar, bottom safe-area inset)
```

The old `SafeAreaView` around everything is replaced by explicit insets: the header pads the top inset, the tab bar
pads the bottom inset. This keeps screen backgrounds edge-to-edge and the inset math in one testable place.

## 2. Tab bar

Custom `tabBar` for `@react-navigation/bottom-tabs` (no new library):
- One `motion/Pressable` per tab (press scale + light haptic, both off under reduced motion), `accessibilityRole="tab"`,
  `accessibilityState.selected`, 44 px minimum touch target, one-line labels.
- A pill **indicator** behind the active tab slides to the new index (`motion/SlidingIndicator`, Reanimated `withTiming`,
  token duration `base`, standard easing). Under reduced motion (or before the preference is known) it jumps.
- Pure geometry in `src/shell/logic.ts`: `tabWidth`, `indicatorX`, `tabBarHeight(bottomInset)`.
- Icons stay the existing emoji glyphs (no icon font added to the bundle); the active tab is shown by the pill,
  label colour and weight, not by tinting.

Reanimated may only be imported under `src/motion` (existing test), so new animated primitives
(`SlidingIndicator`, `Pulse`) are added to the motion system and the shell composes them.

## 3. Screen transitions

- Tabs: `animation: 'shift'` with a token-duration timing spec; `'none'` under reduced motion.
- Stack: CameraScan keeps `fullScreenModal` + `slide_from_bottom`; `'none'` under reduced motion.
- Pure selectors `tabTransition(reduced)` / `stackTransition(reduced)` in `src/shell/logic.ts`.

## 4. Typography helper (real fonts)

`useAppFonts` loads 15 Expo font files, but nothing used them: the generated `fonts` tokens are CSS stacks, which
React Native cannot use. `src/theme/fontFamily.ts` (pure, no RN import) maps `(role, weight)` to the exact family
name registered by `useFonts`:

| Role | Family | Loaded weights |
|---|---|---|
| display | Fraunces | 400, 500, 600 |
| headline | PlusJakartaSans | 500, 600, 700, 800 |
| sans (body/UI) | Inter | 400, 500, 600, 700 |
| mono | JetBrainsMono | 400, 500, 600, 700 |

An unloaded weight resolves to the nearest loaded one (ties go heavier). The helper returns `{ fontFamily }` only:
callers must not also set `fontWeight` (Android would synthesise or fall back). A small type ramp
(`textStyles.title`, `.label`, `.body`, ...) combines family, size and line height from the existing scale. A test
checks every family the helper can return is imported in `useAppFonts.ts` (and vice versa).

Used by the shell (header, tab bar, Button, EmptyState). Screen text keeps the system font until each screen is redesigned.

## 5. Deferred WS0 fixes (each with a test)

- `useAppFonts`: a timeout (`FONT_LOAD_TIMEOUT_MS`) after which the app renders with system fonts, so the splash can
  never hang; pure `fontGate()` decides. Load errors log through `devWarn` (only in `__DEV__`), no raw `console.warn`.
- `Pressable`: the caller's `transform` is kept and the press scale is appended (`withPressScale`), not replaced.
- `Reveal`: animates at most once, and only if motion is allowed on its first run; a late prime (unknown → allowed)
  does not replay a mounted Reveal (`revealAction()`).
- `App.tsx`: the reduce-motion prime timer is cleared when the prime settles.

## 6. Browser preview

`npm run web` (`expo start --web`, Metro bundler) with `react-native-web`, `react-dom`, `@expo/metro-runtime` at the
versions Expo SDK 52 pins (`bundledNativeModules.json`). Those packages resolve only for the web platform, so the
Android/iOS bundles do not change (checked by the Android export size). It is a **preview, not a device run**:
no haptics, no native stack/screens behaviour, no camera parity, fonts load through `@font-face`, `SecureStore`
has no web backend, layout uses the browser's text metrics. Platform guards are added only where web would crash or
throw, and are either `Platform.OS === 'web'` branches that leave the native path unchanged or `*.web.ts` files that
native bundles never include.

## 7. Bundle budget

Importing `src/motion` from the shell pulls Reanimated into the Android bundle. Measure
`npx expo export --platform android` before (2,361,153 B at a3fffaa) and after, run `check:mobile-budget`, and record
both in `performance-budgets.md` (mobile section). `react-native-gesture-handler` stays unimported (no gesture is used;
it costs about 934 KB). The budget constant is only tightened if the after-size leaves clear margin, with the rationale
written down; it is never raised.

## 8. Out of scope

Screen content redesign, icon set, Hindi/Marathi copy changes, gesture-driven interactions, moving the header into
the navigator (CameraScan still opens below the app header, as before), device or emulator runs (none available).
