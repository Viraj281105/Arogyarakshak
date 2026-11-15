import { readReducedMotion } from "./useReducedMotion";

type DocWithTransition = { startViewTransition?: (cb: () => void | Promise<void>) => unknown };

/**
 * Runs `go` (e.g. `router.push`) inside a View Transition when the browser supports it and the
 * user allows motion; otherwise calls `go()` directly. Does not use Next's experimental flag.
 */
export function navigateWithTransition(go: () => void): void {
  const doc = typeof document === "undefined" ? undefined : (document as unknown as DocWithTransition);
  if (!doc || typeof doc.startViewTransition !== "function" || readReducedMotion()) {
    go();
    return;
  }
  doc.startViewTransition(() => {
    go();
  });
}
