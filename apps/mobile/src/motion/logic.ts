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
