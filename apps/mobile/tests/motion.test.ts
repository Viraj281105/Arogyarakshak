import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { readTree } from './sourceTree';
import {
  countUpValue,
  shouldAnimate,
  subscribeReducedMotion,
  readReducedMotion,
  type AccessibilityInfoLike,
} from '../src/motion/logic';

const SRC = join(process.cwd(), 'src');
const MOTION = join(SRC, 'motion');

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
}

function fakeA11y(initial: boolean) {
  const listeners = new Set<(v: boolean) => void>();
  let removed = 0;
  const a11y: AccessibilityInfoLike = {
    isReduceMotionEnabled: async () => initial,
    addEventListener: (_name, cb) => {
      listeners.add(cb);
      return {
        remove() {
          removed += 1;
          listeners.delete(cb);
        },
      };
    },
  };
  return { a11y, emit: (v: boolean) => listeners.forEach((l) => l(v)), removed: () => removed };
}

test('readReducedMotion returns the initial platform value', async () => {
  assert.equal(await readReducedMotion(fakeA11y(true).a11y), true);
  assert.equal(await readReducedMotion(fakeA11y(false).a11y), false);
});

test('readReducedMotion falls back to false when the platform read rejects', async () => {
  const a11y: AccessibilityInfoLike = {
    isReduceMotionEnabled: async () => {
      throw new Error('boom');
    },
    addEventListener: () => ({ remove() {} }),
  };
  assert.equal(await readReducedMotion(a11y), false);
});

test('a reduceMotionChanged event updates subscribers', () => {
  const f = fakeA11y(false);
  const seen: boolean[] = [];
  subscribeReducedMotion(f.a11y, (v) => seen.push(v));
  f.emit(true);
  f.emit(false);
  assert.deepEqual(seen, [true, false]);
});

test('unsubscribe calls remove() exactly once and is idempotent', () => {
  const f = fakeA11y(false);
  const seen: boolean[] = [];
  const off = subscribeReducedMotion(f.a11y, (v) => seen.push(v));
  off();
  off();
  assert.equal(f.removed(), 1);
  f.emit(true);
  assert.deepEqual(seen, []);
});

test('countUpValue is clamped, anchored and monotonic', () => {
  assert.equal(countUpValue(0, 100), 0);
  assert.equal(countUpValue(1, 100), 100);
  assert.equal(countUpValue(-3, 100), 0);
  assert.equal(countUpValue(7, 100), 100);
  let prev = 0;
  for (let i = 0; i <= 100; i++) {
    const v = countUpValue(i / 100, 250);
    assert.ok(v >= prev, `non-monotonic at ${i}`);
    prev = v;
  }
});

test('shouldAnimate truth table', () => {
  assert.equal(shouldAnimate(false), true);
  assert.equal(shouldAnimate(true), false);
});

test('react-native-reanimated is imported only under src/motion', () => {
  for (const file of walk(SRC)) {
    if (!/\.tsx?$/.test(file) || file.startsWith(MOTION)) continue;
    assert.ok(
      !/from\s+['"]react-native-reanimated['"]/.test(readFileSync(file, 'utf-8')),
      `reanimated imported outside src/motion: ${file}`,
    );
  }
});

test('logic.ts imports neither react-native nor reanimated', () => {
  const logic = readFileSync(join(MOTION, 'logic.ts'), 'utf-8');
  assert.ok(!/from\s+['"]react-native/.test(logic));
});

test('useReducedMotion subscribes to reduceMotionChanged and unsubscribes in cleanup', () => {
  const logic = readFileSync(join(MOTION, 'logic.ts'), 'utf-8');
  assert.match(logic, /reduceMotionChanged/);
  assert.match(logic, /\.remove\(\)/);
  const hook = readFileSync(join(MOTION, 'useReducedMotion.ts'), 'utf-8');
  assert.match(hook, /subscribeReducedMotion\(/);
  assert.match(hook, /readReducedMotion\(/);
  assert.match(hook, /return\s*\(\)\s*=>|return\s+\w+;|return\s+unsubscribe/);
});

test('every exported pattern component and tap() reference useReducedMotion', () => {
  for (const f of ['Reveal', 'Parallax', 'Pressable', 'CountUp']) {
    const src = readFileSync(join(MOTION, `${f}.tsx`), 'utf-8');
    assert.match(src, /useReducedMotion/, `${f} must branch on useReducedMotion`);
  }
  const index = readFileSync(join(MOTION, 'index.ts'), 'utf-8');
  for (const n of ['Reveal', 'Parallax', 'Pressable', 'CountUp', 'useReducedMotion', 'tap']) {
    assert.match(index, new RegExp(String.raw`\b${n}\b`), `index must export ${n}`);
  }
});

test('haptics tap is a no-op under reduced motion and swallows errors', () => {
  const h = readFileSync(join(MOTION, 'haptics.ts'), 'utf-8');
  assert.match(h, /readReducedMotion|shouldAnimate/);
  assert.match(h, /catch/);
});

test('motion sources use token durations, not numeric literals', () => {
  const src = readTree(MOTION);
  assert.ok(!/duration\s*:\s*\d/.test(src), 'numeric duration literal found');
  assert.ok(!/withTiming\([^)]*\{\s*duration\s*:\s*\d+/.test(src));
  assert.match(src, /generated\/tokens/);
});
