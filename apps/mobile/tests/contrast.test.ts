import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { contrastRatio, over, luminance, AA_TEXT, AA_NON_TEXT } from '../src/theme/contrast';
import { darkColors, lightColors } from '../src/theme/colors';
import { contrastPairs, buttonSwatch } from '../src/components/ui/tones';

const THEMES = { dark: darkColors, light: lightColors } as const;

test('contrast helper matches WCAG reference values', () => {
  assert.equal(Math.round(contrastRatio('#000000', '#FFFFFF') * 100) / 100, 21);
  assert.equal(contrastRatio('#777777', '#777777'), 1);
  assert.ok(Math.abs(contrastRatio('#767676', '#FFFFFF') - 4.54) < 0.01);
  assert.equal(over('rgba(0, 0, 0, 0.5)', '#FFFFFF'), '#808080');
  assert.throws(() => luminance('rgba(0,0,0,0.5)'));
});

test('the web-reported failure is real and fixed: white on dark brandCyan fails, the action pair passes', () => {
  assert.ok(contrastRatio('#FFFFFF', darkColors.brandCyan) < AA_TEXT, 'premise: white on dark brandCyan fails AA');
  for (const [name, p] of Object.entries(THEMES)) {
    const s = buttonSwatch(p, 'primary');
    assert.equal(s.bg, p.actionPrimary, `${name}: primary fill is actionPrimary`);
    assert.equal(s.fg, p.textOnAction, `${name}: primary label is textOnAction`);
    assert.ok(contrastRatio(s.fg, s.bg!) >= AA_TEXT);
  }
});

for (const [theme, palette] of Object.entries(THEMES)) {
  test(`every shared-component pairing meets AA in the ${theme} theme`, () => {
    const pairs = contrastPairs(palette);
    assert.ok(pairs.length > 80, `expected the full pair list, got ${pairs.length}`);
    const failures = pairs
      .map((p) => ({ ...p, ratio: contrastRatio(p.fg, p.bg) }))
      .filter((p) => p.ratio < p.min)
      .map((p) => `${p.id}: ${p.fg} on ${p.bg} = ${p.ratio.toFixed(2)} (needs ${p.min})`);
    assert.deepEqual(failures, [], failures.join('\n'));
    for (const p of pairs) assert.ok(p.min === AA_TEXT || p.min === AA_NON_TEXT, p.id);
  });
}

// The pair list is only meaningful if the components draw colours exclusively through tones.ts.
const SHARED = [
  'Button.tsx',
  'Badge.tsx',
  'Header.tsx',
  'OfflineBanner.tsx',
  'Skeleton.tsx',
  'TabBar.tsx',
];

test('shared components contain no colour literals (all colours come from tokens via tones.ts)', () => {
  for (const f of SHARED) {
    const src = readFileSync(join(process.cwd(), 'src', 'components', f), 'utf-8');
    assert.doesNotMatch(src, /#[0-9a-fA-F]{3,8}\b/, `${f} has a hex colour`);
    assert.doesNotMatch(src, /rgba?\(/, `${f} has an rgb() colour`);
    assert.doesNotMatch(src, /['"](white|black)['"]/i, `${f} has a named colour`);
  }
});
