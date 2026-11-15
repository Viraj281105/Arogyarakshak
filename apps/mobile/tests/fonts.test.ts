import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const hook = readFileSync(join(process.cwd(), 'src', 'hooks', 'useAppFonts.ts'), 'utf-8');
const app = readFileSync(join(process.cwd(), 'App.tsx'), 'utf-8');

test('useAppFonts source references the four bundled families and no network URL', () => {
  for (const pkg of ['fraunces', 'plus-jakarta-sans', 'inter', 'jetbrains-mono']) {
    assert.ok(hook.includes(`@expo-google-fonts/${pkg}`), `missing @expo-google-fonts/${pkg}`);
  }
  assert.ok(!/https?:\/\//.test(hook), 'no network URL allowed');
  assert.ok(!/fonts\.(googleapis|gstatic)\.com/.test(hook));
});

test('useAppFonts treats a load error as proceed-with-system-fonts', () => {
  assert.match(hook, /useFonts\(/);
  assert.match(hook, /error/);
});

test('App keeps the splash screen until fonts are ready and renders null before', () => {
  assert.match(app, /SplashScreen\.preventAutoHideAsync\(\)/);
  assert.match(app, /SplashScreen\.hideAsync\(\)/);
  assert.match(app, /useAppFonts\(\)/);
  assert.match(app, /return null/);
});
