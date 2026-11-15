"use client";

import { useEffect } from "react";
import { useReducedMotion } from "./useReducedMotion";

/**
 * Optional smooth wheel scrolling. Lenis is imported dynamically after mount, so it is a
 * separate lazy chunk and costs nothing on first load. Skipped entirely under reduced motion
 * and destroyed if the preference flips on. Keyboard, in-page find and touch scrolling stay
 * native (no syncTouch); anchor links are handled by Lenis (`anchors: true`).
 */
export default function SmoothScroll() {
  const reduced = useReducedMotion();

  useEffect(() => {
    if (reduced) return;
    let cancelled = false;
    let lenis: { destroy(): void } | undefined;
    import("lenis").then(({ default: Lenis }) => {
      if (cancelled) return;
      lenis = new Lenis({ autoRaf: true, anchors: true, syncTouch: false });
    });
    return () => {
      cancelled = true;
      lenis?.destroy();
    };
  }, [reduced]);

  return null;
}
