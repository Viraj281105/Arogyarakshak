// Pure motion logic: no react-native / reanimated imports, so it is unit-testable under tsx.
import { motion } from '../generated/tokens';

export interface AccessibilityInfoLike {
  isReduceMotionEnabled(): Promise<boolean>;
  addEventListener(
    name: 'reduceMotionChanged',
    cb: (v: boolean) => void,
  ): { remove(): void };
}

/** Initial OS-level "reduce motion" value. A rejected platform read means "motion allowed". */
export async function readReducedMotion(a11y: AccessibilityInfoLike): Promise<boolean> {
  try {
    return await a11y.isReduceMotionEnabled();
  } catch {
    return false;
  }
}

/** Subscribes to reduceMotionChanged. The returned unsubscribe removes the listener once. */
export function subscribeReducedMotion(
  a11y: AccessibilityInfoLike,
  listener: (v: boolean) => void,
): () => void {
  const sub = a11y.addEventListener('reduceMotionChanged', listener);
  let done = false;
  return () => {
    if (done) return;
    done = true;
    sub.remove();
  };
}

export interface ReducedMotionStore {
  /** undefined = not yet known. */
  get(): boolean | undefined;
  /** Initial read. Never overwrites a value an event already set; a failed read means false. */
  prime(): Promise<void>;
  subscribe(listener: () => void): () => void;
}

/** Cache of the OS preference so components and haptics can read it synchronously. */
export function createReducedMotionStore(a11y: AccessibilityInfoLike): ReducedMotionStore {
  let value: boolean | undefined;
  const listeners = new Set<() => void>();
  const set = (v: boolean) => {
    if (value === v) return;
    value = v;
    listeners.forEach((l) => l());
  };
  // Lives for the app's lifetime, so the event subscription is never removed.
  subscribeReducedMotion(a11y, set);
  return {
    get: () => value,
    async prime() {
      const initial = await readReducedMotion(a11y);
      if (value === undefined) set(initial);
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  };
}

/** Unknown is treated as reduced, so nobody sees a hidden / start-of-animation state. */
export function isReduced(value: boolean | undefined): boolean {
  return value !== false;
}

export function motionMode(value: boolean | undefined): 'animate' | 'final' {
  return isReduced(value) ? 'final' : 'animate';
}

/** Haptics fire only when the preference is known to allow motion (no bridge call per press). */
export function shouldHaptic(value: boolean | undefined): boolean {
  return value === false;
}

/** Skeleton pulse range; reduced motion shows the max (static, readable) value. */
export const PULSE_MIN_OPACITY = 0.45;
export const PULSE_MAX_OPACITY = 1;

/** Haptics exist only on device platforms (the browser preview has no haptic engine). */
export function hapticsSupported(os: string): boolean {
  return os === 'ios' || os === 'android';
}

// RN transform entries are single-key objects ({ rotate: '5deg' }, { scale: 2 }, ...).
export type TransformEntry = Record<string, unknown>;

/**
 * Splits a flattened style into its array transform and everything else, so the press scale can
 * be appended to the caller's transform instead of replacing it. A non-array transform (string
 * form) is left on `rest` untouched.
 */
export function splitTransform<S extends { transform?: unknown }>(
  style: S | null | undefined,
): { transform: TransformEntry[]; rest: Omit<S, 'transform'> | Record<string, never> } {
  if (!style) return { transform: [], rest: {} };
  if (!Array.isArray(style.transform)) return { transform: [], rest: style };
  const { transform, ...rest } = style;
  return { transform: transform as TransformEntry[], rest };
}

/** Caller transform followed by the press scale. Runs inside a Reanimated worklet. */
export function withPressScale(base: TransformEntry[] | undefined, scale: number): TransformEntry[] {
  'worklet';
  return [...(base ?? []), { scale }];
}

/**
 * What a Reveal does when its effect runs. It animates at most once, and only if motion is
 * allowed the first time; a later change (e.g. a late reduce-motion prime, unknown -> allowed)
 * never replays it. Turning reduced motion on jumps to the final state.
 */
export function revealAction(started: boolean, reduced: boolean): 'animate' | 'final' | 'none' {
  if (reduced) return 'final';
  return started ? 'none' : 'animate';
}

/** Animate only when the user has not asked for reduced motion. */
export function shouldAnimate(reducedMotion: boolean): boolean {
  return !reducedMotion;
}

// Parse the token's cubic-bezier(x1,y1,x2,y2) so the count-up shares the standard easing.
export const STANDARD_BEZIER: [number, number, number, number] = (() => {
  const m = /cubic-bezier\(([^)]+)\)/.exec(motion.easing.standard);
  const n = (m ? m[1] : '0.2,0,0,1').split(',').map(Number);
  return [n[0], n[1], n[2], n[3]];
})();
const [X1, Y1, X2, Y2] = STANDARD_BEZIER;

const bez = (t: number, a: number, b: number) =>
  3 * a * (1 - t) * (1 - t) * t + 3 * b * (1 - t) * t * t + t * t * t;

function standardEasing(x: number): number {
  let lo = 0;
  let hi = 1;
  for (let i = 0; i < 30; i++) {
    const mid = (lo + hi) / 2;
    if (bez(mid, X1, X2) < x) lo = mid;
    else hi = mid;
  }
  return bez((lo + hi) / 2, Y1, Y2);
}

/** Value of a count-up at `progress` (0..1, clamped), eased with the standard motion easing. */
export function countUpValue(progress: number, to: number): number {
  const p = Math.min(1, Math.max(0, progress));
  if (p === 0) return 0;
  if (p === 1) return to;
  return to * standardEasing(p);
}
