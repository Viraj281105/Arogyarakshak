"use client";

import { RefObject, useEffect } from "react";

const REDUCED = "(prefers-reduced-motion: reduce)";

/**
 * Reveals every `[data-reveal]` element inside `root` as it scrolls into view by adding
 * `is-visible`. Content is only hidden once this hook has marked the root ready, so the
 * page reads fine without JavaScript, and reduced-motion viewers get everything at once.
 */
export function useScrollReveal(root: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = root.current;
    if (!el) return;
    const targets = Array.from(el.querySelectorAll<HTMLElement>("[data-reveal]"));
    const reduced = window.matchMedia?.(REDUCED).matches;
    if (reduced || typeof IntersectionObserver === "undefined") {
      targets.forEach((t) => t.classList.add("is-visible"));
      return;
    }
    el.setAttribute("data-reveal-ready", "");
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target);
          }
        }
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.12 }
    );
    targets.forEach((t) => io.observe(t));
    return () => {
      io.disconnect();
      el.removeAttribute("data-reveal-ready");
    };
  }, [root]);
}

/**
 * Writes how far `target` has travelled through the viewport (0 entering at the bottom,
 * 1 leaving at the top) into the CSS variable `name` on it. Reduced motion pins it at 1.
 */
export function useScrollProgress(target: RefObject<HTMLElement | null>, name = "--scroll-progress") {
  useEffect(() => {
    const el = target.current;
    if (!el) return;
    if (window.matchMedia?.(REDUCED).matches) {
      el.style.setProperty(name, "1");
      return;
    }
    let frame = 0;
    const update = () => {
      frame = 0;
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight || 1;
      const progress = Math.min(1, Math.max(0, (vh - rect.top) / (vh + rect.height)));
      el.style.setProperty(name, progress.toFixed(3));
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      if (frame) cancelAnimationFrame(frame);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, [target, name]);
}
