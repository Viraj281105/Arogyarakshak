import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  fontFamily,
  font,
  LOADED_FONT_FAMILIES,
  textStyles,
  type FontRole,
} from '../src/theme/fontFamily';
import {
  tabWidth,
  indicatorX,
  tabBarHeight,
  tabTransition,
  stackTransition,
  navigationTheme,
  TAB_BAR_BASE_HEIGHT,
} from '../src/shell/logic';
import { withPressScale, splitTransform, revealAction } from '../src/motion/logic';
import { fontGate, FONT_LOAD_TIMEOUT_MS } from '../src/hooks/fontGate';
import { createDevLogger } from '../src/logging';
import { darkColors, lightColors } from '../src/theme/colors';
import { spacing } from '../src/theme/spacing';

const ROOT = process.cwd();
const read = (...p: string[]) => readFileSync(join(ROOT, ...p), 'utf-8');

// ---------- typography helper ----------

test('fontFamily maps role + loaded weight to the exact Expo family name', () => {
  assert.equal(fontFamily('sans', '400'), 'Inter_400Regular');
  assert.equal(fontFamily('sans', '700'), 'Inter_700Bold');
  assert.equal(fontFamily('display', '600'), 'Fraunces_600SemiBold');
  assert.equal(fontFamily('headline', '800'), 'PlusJakartaSans_800ExtraBold');
  assert.equal(fontFamily('mono', '500'), 'JetBrainsMono_500Medium');
});

test('fontFamily resolves an unloaded weight to the nearest loaded one (ties go heavier)', () => {
  assert.equal(fontFamily('display', '800'), 'Fraunces_600SemiBold'); // max loaded 600
  assert.equal(fontFamily('headline', '400'), 'PlusJakartaSans_500Medium'); // min loaded 500
  assert.equal(fontFamily('sans', '800'), 'Inter_700Bold');
  assert.equal(fontFamily('sans', '300'), 'Inter_400Regular');
});

test('font() returns only fontFamily (no fontWeight, which Android would synthesise)', () => {
  const s = font('sans', '600');
  assert.deepEqual(s, { fontFamily: 'Inter_600SemiBold' });
  assert.ok(!('fontWeight' in s));
});

test('every family the helper can return is loaded by useAppFonts, and every loaded one is mapped', () => {
  const hook = read('src', 'hooks', 'useAppFonts.ts');
  const imported = new Set([...hook.matchAll(/import \{ (\w+) \} from '@expo-google-fonts/g)].map((m) => m[1]));
  const roles: FontRole[] = ['display', 'headline', 'sans', 'mono'];
  const weights = ['100', '200', '300', '400', '500', '600', '700', '800', '900'] as const;
  for (const r of roles) for (const w of weights) {
    const fam = fontFamily(r, w);
    assert.ok(imported.has(fam), `${r}/${w} -> ${fam} is not loaded by useAppFonts`);
  }
  assert.deepEqual([...imported].sort(), [...LOADED_FONT_FAMILIES].sort());
});

test('textStyles presets use real families and no fontWeight', () => {
  for (const [name, style] of Object.entries(textStyles)) {
    assert.ok(LOADED_FONT_FAMILIES.includes(style.fontFamily), `${name} uses ${style.fontFamily}`);
    assert.ok(!('fontWeight' in style), `${name} sets fontWeight`);
    assert.ok(style.lineHeight >= style.fontSize, `${name} lineHeight < fontSize`);
  }
});

test('fontFamily.ts is pure (no react-native import, so it is testable and shared)', () => {
  assert.ok(!/from\s+['"]react-native/.test(read('src', 'theme', 'fontFamily.ts')));
});

// ---------- tab bar / transitions ----------

test('tab geometry: equal widths, indicator at index * width, guarded inputs', () => {
  assert.equal(tabWidth(360, 6), 60);
  assert.equal(tabWidth(0, 6), 0);
  assert.equal(tabWidth(360, 0), 0);
  assert.equal(indicatorX(0, 60), 0);
  assert.equal(indicatorX(3, 60), 180);
  assert.equal(indicatorX(-1, 60), 0);
});

test('tab bar height adds the bottom safe-area inset (min spacing.sm) and keeps a 44px target', () => {
  assert.equal(tabBarHeight(0), TAB_BAR_BASE_HEIGHT + spacing.sm);
  assert.equal(tabBarHeight(34), TAB_BAR_BASE_HEIGHT + 34);
  assert.ok(TAB_BAR_BASE_HEIGHT >= spacing.minTouchTarget);
});

test('screen transitions are off under reduced motion (and while unknown)', () => {
  assert.equal(tabTransition(true), 'none');
  assert.equal(tabTransition(false), 'shift');
  assert.equal(stackTransition(true), 'none');
  assert.equal(stackTransition(false), 'slide_from_bottom');
});

test('navigationTheme is built from tokens for both schemes, with real font families', () => {
  const d = navigationTheme(true, darkColors);
  assert.equal(d.dark, true);
  assert.equal(d.colors.background, darkColors.bgBase);
  assert.equal(d.colors.card, darkColors.bgSurface);
  assert.equal(d.colors.text, darkColors.textPrimary);
  assert.equal(d.colors.border, darkColors.borderSubtle);
  const l = navigationTheme(false, lightColors);
  assert.equal(l.dark, false);
  assert.equal(l.colors.background, lightColors.bgBase);
  for (const f of Object.values(d.fonts)) assert.ok(LOADED_FONT_FAMILIES.includes(f.fontFamily));
});

// ---------- deferred motion fixes ----------

test('Pressable press scale is appended to (not replacing) a caller transform', () => {
  assert.deepEqual(withPressScale([{ rotate: '5deg' }, { translateX: 3 }], 0.97), [
    { rotate: '5deg' },
    { translateX: 3 },
    { scale: 0.97 },
  ]);
  assert.deepEqual(withPressScale(undefined, 1), [{ scale: 1 }]);
});

test('splitTransform separates the caller transform from the rest of the style', () => {
  const { transform, rest } = splitTransform({ padding: 4, transform: [{ rotate: '1deg' }] });
  assert.deepEqual(transform, [{ rotate: '1deg' }]);
  assert.deepEqual(rest, { padding: 4 });
  assert.deepEqual(splitTransform(undefined), { transform: [], rest: {} });
  // A non-array (string) transform is not mergeable: it stays on rest untouched.
  assert.deepEqual(splitTransform({ transform: 'rotate(1deg)' as unknown as [] }).transform, []);
});

test('Pressable uses splitTransform + withPressScale', () => {
  const src = read('src', 'motion', 'Pressable.tsx');
  assert.match(src, /splitTransform\(/);
  assert.match(src, /withPressScale\(/);
});

test('revealAction: animates at most once, never replays after a late prime', () => {
  // first run, preference unknown/reduced -> final; a late prime (reduced -> allowed) must not replay
  assert.equal(revealAction(false, true), 'final');
  assert.equal(revealAction(true, false), 'none');
  // first run with motion allowed -> animate once; later runs never animate again
  assert.equal(revealAction(false, false), 'animate');
  assert.equal(revealAction(true, false), 'none');
  // switching reduce-motion on mid-way jumps to the final state
  assert.equal(revealAction(true, true), 'final');
});

test('Reveal uses revealAction and a started ref', () => {
  const src = read('src', 'motion', 'Reveal.tsx');
  assert.match(src, /revealAction\(/);
  assert.match(src, /useRef/);
});

// ---------- fonts gate + dev logger ----------

test('fontGate: ready on load, on error, or after the timeout; never stuck', () => {
  assert.deepEqual(fontGate({ loaded: false, error: null, timedOut: false }), { ready: false, reason: 'pending' });
  assert.deepEqual(fontGate({ loaded: true, error: null, timedOut: false }), { ready: true, reason: 'loaded' });
  assert.deepEqual(fontGate({ loaded: false, error: new Error('x'), timedOut: false }), { ready: true, reason: 'error' });
  assert.deepEqual(fontGate({ loaded: false, error: null, timedOut: true }), { ready: true, reason: 'timeout' });
  assert.deepEqual(fontGate({ loaded: true, error: null, timedOut: true }), { ready: true, reason: 'loaded' });
  assert.ok(FONT_LOAD_TIMEOUT_MS > 0 && FONT_LOAD_TIMEOUT_MS <= 10_000);
});

test('useAppFonts uses the timeout gate and no raw console.warn', () => {
  const hook = read('src', 'hooks', 'useAppFonts.ts');
  assert.match(hook, /fontGate\(/);
  assert.match(hook, /setTimeout\(/);
  assert.match(hook, /clearTimeout\(/);
  assert.ok(!/console\.warn/.test(hook));
  assert.match(hook, /devWarn/);
});

test('createDevLogger only writes in development', () => {
  const lines: unknown[][] = [];
  createDevLogger(true, (...a) => lines.push(a)).warn('a', 1);
  createDevLogger(false, (...a) => lines.push(a)).warn('b');
  assert.deepEqual(lines, [['a', 1]]);
});

test('App clears the reduce-motion prime timer once the prime settles', () => {
  const app = read('App.tsx');
  assert.match(app, /clearTimeout\(timer\)/);
  const done = /const done = \(\) => \{([\s\S]*?)\};/.exec(app);
  assert.ok(done && /clearTimeout\(timer\)/.test(done[1]), 'done() must clear the timer');
});

// ---------- shell wiring contracts ----------

test('shell does not import react-native-gesture-handler (no gesture used; ~934 KB)', () => {
  for (const f of ['App.tsx', 'src/navigation/BottomTabNavigator.tsx', 'src/navigation/RootNavigator.tsx', 'src/components/TabBar.tsx']) {
    assert.ok(!/react-native-gesture-handler/.test(read(f)), f);
  }
});

test('the tab navigator uses the custom tab bar and reduced-motion-aware transitions', () => {
  const nav = read('src', 'navigation', 'BottomTabNavigator.tsx');
  assert.match(nav, /tabBar=\{/);
  assert.match(nav, /tabTransition\(/);
  const root = read('src', 'navigation', 'RootNavigator.tsx');
  assert.match(root, /stackTransition\(/);
});

test('the tab bar is accessible: tab role, selected state, motion Pressable', () => {
  const bar = read('src', 'components', 'TabBar.tsx');
  assert.match(bar, /accessibilityRole="tab"/);
  assert.match(bar, /selected/);
  assert.match(bar, /from '\.\.\/motion'/);
  assert.match(bar, /SlidingIndicator/);
});

test('Button and Card are on the motion system (no TouchableOpacity)', () => {
  const button = read('src', 'components', 'Button.tsx');
  assert.match(button, /Pressable/);
  assert.ok(!/TouchableOpacity/.test(button));
  const card = read('src', 'components', 'Card.tsx');
  assert.match(card, /Reveal/);
  const header = read('src', 'components', 'Header.tsx');
  assert.ok(!/TouchableOpacity/.test(header));
});

test('App uses a token-built navigation theme and explicit safe-area insets', () => {
  const app = read('App.tsx');
  assert.match(app, /navigationTheme\(/);
  assert.match(app, /StatusBar/);
  assert.ok(!/<SafeAreaView/.test(app), 'insets are applied by the header and tab bar');
});
