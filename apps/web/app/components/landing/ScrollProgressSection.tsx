"use client";

import React, { useRef } from "react";
import { useScrollProgress } from "../../hooks/useScrollMotion";

/**
 * A <section> that writes its scroll progress (0..1) into the CSS variable `progressVar`
 * (useScrollProgress; pinned at 1 under reduced motion). The only client code the hero and
 * journey sections need, so their content can stay Server Components (no client JS).
 */
export function ScrollProgressSection({
  progressVar,
  className,
  labelledBy,
  children,
}: {
  progressVar: string;
  className: string;
  labelledBy: string;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLElement>(null);
  useScrollProgress(ref, progressVar);
  return (
    <section ref={ref} className={className} aria-labelledby={labelledBy}>
      {children}
    </section>
  );
}
