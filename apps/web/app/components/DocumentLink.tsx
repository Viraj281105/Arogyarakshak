import type { AnchorHTMLAttributes } from "react";

/**
 * A plain anchor that performs a full document navigation on purpose. Used by the 404 and error
 * pages: after a failure a fresh load is the robust choice, and not importing next/link keeps
 * the Link module out of the error/not-found chunks that every route loads (WS4 bundle budget).
 * Everywhere else, use next/link or the shell's TransitionLink.
 */
export function DocumentLink(props: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
  return <a {...props} />;
}
