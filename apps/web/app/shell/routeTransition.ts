// Coordinates a View Transition with a client navigation: TransitionLink starts a transition
// whose update callback waits for `waitForRouteCommit()`, and the shell calls `routeCommitted()`
// from an effect when the pathname changes (the new page is in the DOM by then).

let pending: { resolve: () => void; timer: ReturnType<typeof setTimeout> } | null = null;

function settle(): void {
  if (!pending) return;
  clearTimeout(pending.timer);
  const { resolve } = pending;
  pending = null;
  resolve();
}

/** Longest a View Transition waits for the new route before it finishes anyway. */
export const ROUTE_COMMIT_TIMEOUT_MS = 400;

/**
 * Resolves when the next route commits, or after `timeoutMs` at the latest: the page is frozen on
 * the transition snapshot while this is pending, so a slow, failed or cancelled navigation must
 * not hold it. On timeout the transition finishes and the navigation simply continues without it.
 * A newer call settles the previous one first.
 */
export function waitForRouteCommit(timeoutMs = ROUTE_COMMIT_TIMEOUT_MS): Promise<void> {
  settle();
  return new Promise<void>((resolve) => {
    pending = { resolve, timer: setTimeout(settle, timeoutMs) };
  });
}

/** Called by the shell when the pathname has changed. */
export function routeCommitted(): void {
  settle();
}

export interface ClickLike {
  button: number;
  metaKey: boolean;
  ctrlKey: boolean;
  shiftKey: boolean;
  altKey: boolean;
  defaultPrevented: boolean;
}

/**
 * Pure: should this click become a client navigation inside a View Transition? Only a plain
 * primary click to another pathname of this origin. Modified clicks (new tab/window), other
 * targets, external URLs and same-page hash links keep the browser's native behaviour.
 */
export function shouldTransition(e: ClickLike, href: string, currentUrl: string, target?: string | null): boolean {
  if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return false;
  if (target && target !== "_self") return false;
  let to: URL;
  let from: URL;
  try {
    from = new URL(currentUrl);
    to = new URL(href, from);
  } catch {
    return false;
  }
  if (to.origin !== from.origin) return false;
  // Only a pathname change commits a new route (the shell resolves the wait on pathname); search-
  // or hash-only links navigate natively instead of holding a transition until the timeout.
  return to.pathname !== from.pathname;
}
