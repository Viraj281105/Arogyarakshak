"use client";

import { useSyncExternalStore } from "react";

export interface MediaQueryListLike {
  matches: boolean;
  addEventListener(type: "change", cb: () => void): void;
  removeEventListener(type: "change", cb: () => void): void;
}

const QUERY = "(prefers-reduced-motion: reduce)";

function defaultMediaQuery(): MediaQueryListLike | undefined {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return undefined;
  return window.matchMedia(QUERY);
}

/** Current OS-level preference. False where there is no window (server / tests). */
export function readReducedMotion(mq: MediaQueryListLike | undefined = defaultMediaQuery()): boolean {
  return mq?.matches ?? false;
}

/** Subscribes to preference changes (OS toggle while the page is open). Returns the unsubscribe. */
export function subscribeReducedMotion(
  listener: () => void,
  mq: MediaQueryListLike | undefined = defaultMediaQuery(),
): () => void {
  if (!mq) return () => {};
  mq.addEventListener("change", listener);
  return () => mq.removeEventListener("change", listener);
}

// Module-level so React keeps one subscription instead of resubscribing on every render.
const subscribe = (cb: () => void) => subscribeReducedMotion(cb);
const getSnapshot = () => readReducedMotion();
const getServerSnapshot = () => false;

/**
 * Reactive reduced-motion preference. The server snapshot is `false`, so this value must only
 * gate whether animation RUNS, never change rendered text or markup (hydration-safe).
 */
export function useReducedMotion(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

/** Animate only when the user allows motion AND the browser supports the effect. */
export function shouldAnimate(opts: { reducedMotion: boolean; supportsScrollTimeline: boolean }): boolean {
  return !opts.reducedMotion && opts.supportsScrollTimeline;
}

// cubic-bezier(0.2, 0, 0, 1): mirrors --motion-easing-standard in generated/tokens.css.
const X1 = 0.2;
const Y1 = 0;
const X2 = 0;
const Y2 = 1;
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
