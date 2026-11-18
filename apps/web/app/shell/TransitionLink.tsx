"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { navigateWithTransition } from "../motion/viewTransition";
import { shouldTransition, waitForRouteCommit } from "./routeTransition";

type Props = React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string };

/**
 * An internal link that navigates on the client inside a View Transition (navigateWithTransition:
 * skipped under reduced motion and where unsupported). It is a real <a href>, so it works without
 * JavaScript, middle-click and "open in new tab" keep native behaviour, and same-page hash links
 * scroll natively. The route is prefetched on hover/focus/touch. Used instead of next/link in the
 * shell; behaviour decisions live in routeTransition.ts (unit-tested).
 */
export const TransitionLink = React.forwardRef<HTMLAnchorElement, Props>(function TransitionLink(
  { href, onClick, onMouseEnter, onFocus, onTouchStart, ...rest },
  ref
) {
  const router = useRouter();
  const prefetch = () => {
    if (!href.startsWith("/")) return;
    try {
      router.prefetch(href.split("#")[0] || "/");
    } catch {
      // Prefetch is an optimisation only.
    }
  };

  return (
    <a
      ref={ref}
      href={href}
      {...rest}
      onMouseEnter={(e) => {
        onMouseEnter?.(e);
        prefetch();
      }}
      onFocus={(e) => {
        onFocus?.(e);
        prefetch();
      }}
      onTouchStart={(e) => {
        onTouchStart?.(e);
        prefetch();
      }}
      onClick={(e) => {
        onClick?.(e);
        if (!shouldTransition(e, href, window.location.href, rest.target)) return;
        e.preventDefault();
        navigateWithTransition(() => {
          const committed = waitForRouteCommit();
          router.push(href);
          return committed;
        });
      }}
    />
  );
});
