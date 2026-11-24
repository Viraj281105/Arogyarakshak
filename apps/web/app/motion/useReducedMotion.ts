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

/** localStorage key of the in-app "Reduce motion" setting (Settings page); "reduce" or absent. */
export const MOTION_PREF_KEY = "arogyarakshak.motion";
const appListeners = new Set<() => void>();

/** True when the in-app setting asks for reduced motion (the pre-paint script in layout.tsx sets it). */
export function appReducedMotion(): boolean {
  return typeof document !== "undefined" && document.documentElement?.getAttribute("data-motion") === "reduce";
}

/** Turns the in-app setting on or off for this browser (a per-viewer convenience, not sensitive). */
export function setAppReducedMotion(on: boolean): void {
  if (typeof document === "undefined") return;
  if (on) document.documentElement.setAttribute("data-motion", "reduce");
  else document.documentElement.removeAttribute("data-motion");
  try {
    if (on) localStorage.setItem(MOTION_PREF_KEY, "reduce");
    else localStorage.removeItem(MOTION_PREF_KEY);
  } catch {
    // storage unavailable: the choice lasts until reload
  }
  appListeners.forEach((l) => l());
}

/** Current preference: the OS setting OR the in-app setting. False where there is no window (server / tests). */
export function readReducedMotion(mq: MediaQueryListLike | undefined = defaultMediaQuery()): boolean {
  return appReducedMotion() || (mq?.matches ?? false);
}

/** Subscribes to preference changes (OS toggle or the in-app setting). Returns the unsubscribe. */
export function subscribeReducedMotion(
  listener: () => void,
  mq: MediaQueryListLike | undefined = defaultMediaQuery(),
): () => void {
  appListeners.add(listener);
  if (!mq) return () => void appListeners.delete(listener);
  mq.addEventListener("change", listener);
  return () => {
    appListeners.delete(listener);
    mq.removeEventListener("change", listener);
  };
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
