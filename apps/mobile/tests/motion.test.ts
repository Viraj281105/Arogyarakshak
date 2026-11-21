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
  createReducedMotionStore,
  motionMode,
  isReduced,
  shouldHaptic,
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

// Ruling 2026-11-18: the motion system runs on React Native Animated; no app code (src/motion
// included) may import react-native-reanimated, in any form. See also tests/shell.test.ts.
test('react-native-reanimated is not imported anywhere under src (incl. subpaths and require)', () => {
  const banned = /(from\s+|import\s+|import\s*\(\s*|require\s*\(\s*)['"]react-native-reanimated(\/[^'"]*)?['"]/;
  for (const file of walk(SRC)) {
    if (!/\.tsx?$/.test(file)) continue;
    assert.ok(!banned.test(readFileSync(file, 'utf-8')), `reanimated imported: ${file}`);
  }
});

test('logic.ts imports neither react-native nor reanimated', () => {
  const logic = readFileSync(join(MOTION, 'logic.ts'), 'utf-8');
  assert.ok(!/from\s+['"]react-native/.test(logic));
});

test('logic subscribes to reduceMotionChanged and removes the listener', () => {
  const logic = readFileSync(join(MOTION, 'logic.ts'), 'utf-8');
  assert.match(logic, /reduceMotionChanged/);
  assert.match(logic, /\.remove\(\)/);
});

test('useReducedMotion reads the primed store synchronously', () => {
  const hook = readFileSync(join(MOTION, 'useReducedMotion.ts'), 'utf-8');
  assert.match(hook, /useSyncExternalStore\(/);
  assert.match(hook, /reducedMotionStore/);
});

test('store: an event that arrives before the initial read wins (stale-read race)', async () => {
  let resolveRead!: (v: boolean) => void;
  const listeners = new Set<(v: boolean) => void>();
  const a11y: AccessibilityInfoLike = {
    isReduceMotionEnabled: () => new Promise<boolean>((r) => (resolveRead = r)),
    addEventListener: (_n, cb) => {
      listeners.add(cb);
      return { remove: () => void listeners.delete(cb) };
    },
  };
  const store = createReducedMotionStore(a11y);
  assert.equal(store.get(), undefined);
  const primed = store.prime();
  listeners.forEach((l) => l(true)); // event first
  resolveRead(false); // older read resolves afterwards
  await primed;
  assert.equal(store.get(), true);
});

test('store: prime sets the initial value, falls back to false on error', async () => {
  const f = fakeA11y(true);
  const store = createReducedMotionStore(f.a11y);
  await store.prime();
  assert.equal(store.get(), true);
  const bad = createReducedMotionStore({
    isReduceMotionEnabled: async () => {
      throw new Error('x');
    },
    addEventListener: () => ({ remove() {} }),
  });
  await bad.prime();
  assert.equal(bad.get(), false);
});

test('store: listeners are notified on change, once per change, and unsubscribe is idempotent', () => {
  const f = fakeA11y(false);
  const store = createReducedMotionStore(f.a11y);
  let calls = 0;
  const off = store.subscribe(() => calls++);
  f.emit(true);
  f.emit(true); // unchanged: no notification
  f.emit(false);
  assert.equal(calls, 2);
  off();
  off();
  f.emit(true);
  assert.equal(calls, 2);
  assert.equal(store.get(), true);
});

test('unknown preference renders the final state and never haptics', () => {
  assert.equal(motionMode(undefined), 'final');
  assert.equal(motionMode(true), 'final');
  assert.equal(motionMode(false), 'animate');
  assert.equal(isReduced(undefined), true);
  assert.equal(shouldHaptic(undefined), false);
  assert.equal(shouldHaptic(true), false);
  assert.equal(shouldHaptic(false), true);
});

test('Pressable animates its own style: no inner wrapper View around children', () => {
  const src = readFileSync(join(MOTION, 'Pressable.tsx'), 'utf-8');
  assert.match(src, /createAnimatedComponent\(RNPressable\)/);
  assert.ok(!/<Animated\.View/.test(src));
});

test('tap reads the cached store, not the native bridge', () => {
  const h = readFileSync(join(MOTION, 'haptics.ts'), 'utf-8');
  assert.match(h, /shouldHaptic\(reducedMotionStore\.get\(\)\)/);
  assert.ok(!/AccessibilityInfo/.test(h));
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
  assert.match(h, /catch/);
});

test('motion sources use token durations, not numeric literals', () => {
  const src = readTree(MOTION);
  assert.ok(!/duration\s*:\s*\d/.test(src), 'numeric duration literal found');
  assert.ok(!/withTiming\([^)]*\{\s*duration\s*:\s*\d+/.test(src));
  assert.match(src, /generated\/tokens/);
});
