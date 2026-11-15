"use client";

import { useEffect } from "react";
import { startSmoothScroll } from "./startSmoothScroll";
import { useReducedMotion } from "./useReducedMotion";

/**
 * Optional smooth wheel scrolling. Lenis is imported dynamically after mount, so it is a
 * separate lazy chunk and costs nothing on first load; if that chunk fails to load, native
 * scrolling simply continues. Skipped entirely under reduced motion and destroyed if the
 * preference flips on. Keyboard, in-page find and touch scrolling stay native (no syncTouch);
 * anchor links are handled by Lenis (`anchors: true`).
 */
export default function SmoothScroll() {
  const reduced = useReducedMotion();

  useEffect(() => {
    if (reduced) return;
    const handle = startSmoothScroll(() => import("lenis"), {
      autoRaf: true,
      anchors: true,
      syncTouch: false,
    });
    return () => handle.stop();
  }, [reduced]);

  return null;
}
