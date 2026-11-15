import type { CSSProperties, ReactNode } from "react";

/**
 * Fades/rises content in as it enters the viewport. Pure CSS (`animation-timeline: view()`):
 * the server-rendered state is the final visible state; browsers without scroll timelines, and
 * users preferring reduced motion, simply see the content. `delay` shifts the start of the
 * entry range by that many percentage points (0-40 is sensible).
 */
export default function Reveal({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  const style = { "--motion-reveal-delay": `${delay}%` } as CSSProperties;
  return (
    <div className="motion-reveal" style={style}>
      {children}
    </div>
  );
}
