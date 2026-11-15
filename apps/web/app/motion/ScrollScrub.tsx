import type { ReactNode } from "react";

/** Scrubs a gentle scale/opacity settle tied to scroll position. Pure CSS; final state by default. */
export default function ScrollScrub({ children }: { children: ReactNode }) {
  return <div className="motion-scrub">{children}</div>;
}
