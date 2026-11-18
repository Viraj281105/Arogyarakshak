import { readReducedMotion } from "./useReducedMotion";

type DocWithTransition = { startViewTransition?: (cb: () => unknown) => unknown };

/**
 * Runs `go` (e.g. `router.push`) inside a View Transition when the browser supports it and the
 * user allows motion; otherwise calls `go()` directly. Does not use Next's experimental flag.
 *
 * If `go` returns a promise (the shell's TransitionLink resolves it once the new route has
 * committed), that promise is handed to the View Transition, so the browser snapshots the NEW
 * page rather than the old one. Callers must make sure it settles (TransitionLink times out).
 */
export function navigateWithTransition(go: () => unknown): void {
  const doc = typeof document === "undefined" ? undefined : (document as unknown as DocWithTransition);
  if (!doc || typeof doc.startViewTransition !== "function" || readReducedMotion()) {
    void go();
    return;
  }
  doc.startViewTransition(() => go());
}
