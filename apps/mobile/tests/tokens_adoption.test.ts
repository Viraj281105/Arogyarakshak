import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { darkColors, lightColors } from '../src/theme/colors';
import { spacing, radii } from '../src/theme/spacing';
import { colors, spacing as genSpacing, radii as genRadii } from '../src/generated/tokens';

// ColorPalette is a subset of the generated palette: every key it declares must
// carry the generated value (single source of truth).
function assertSubset(actual: Record<string, string>, generated: Record<string, string>): void {
  for (const key of Object.keys(actual)) {
    assert.ok(key in generated, `generated palette has no key ${key}`);
    assert.equal(actual[key], generated[key], `${key} differs from generated`);
  }
}

test('darkColors equals generated colors.dark (subset)', () => {
  assertSubset(darkColors as unknown as Record<string, string>, colors.dark);
});

test('lightColors equals generated colors.light (subset)', () => {
  assertSubset(lightColors as unknown as Record<string, string>, colors.light);
});

test('spacing.minTouchTarget is 44 and spacing/radii match generated', () => {
  assert.equal(spacing.minTouchTarget, 44);
  assert.deepEqual({ ...spacing }, { ...genSpacing });
  assert.deepEqual({ ...radii }, { ...genRadii });
});

test('no hex literal remains in src/theme/colors.ts', () => {
  const src = readFileSync(join(process.cwd(), 'src', 'theme', 'colors.ts'), 'utf-8');
  assert.doesNotMatch(src, /#[0-9a-fA-F]{3,8}\b/);
});
