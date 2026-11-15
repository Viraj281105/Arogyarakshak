"use client";

import { useEffect, useState } from "react";
import { countUpValue, useReducedMotion } from "./useReducedMotion";

const defaultFormat = (n: number) => String(Math.round(n));

/**
 * Renders the FINAL formatted value on the server and on first paint. After mount, when motion
 * is allowed, it counts up from 0 once; reduced motion (or its change) keeps the final value.
 * `format` is a function: pass it from a client component (functions cannot cross the RSC boundary).
 */
export default function CountUp({
  to,
  durationMs = 1200,
  format = defaultFormat,
}: {
  to: number;
  durationMs?: number;
  format?: (n: number) => string;
}) {
  const reduced = useReducedMotion();
  // Animated progress is tagged with its target so a changed `to` never shows a stale value.
  const [frame, setFrame] = useState<{ to: number; value: number } | null>(null);

  useEffect(() => {
    if (reduced || durationMs <= 0) return;
    let raf = 0;
    let start: number | undefined;
    const tick = (now: number) => {
      start ??= now;
      const p = Math.min(1, (now - start) / durationMs);
      setFrame({ to, value: countUpValue(p, to) });
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [reduced, to, durationMs]);

  const value = !reduced && frame && frame.to === to ? frame.value : to;
  return <span className="motion-countup">{format(value)}</span>;
}
