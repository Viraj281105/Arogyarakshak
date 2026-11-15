import type { CSSProperties, ReactNode } from "react";

/**
 * Drifts content vertically while it crosses the viewport. Pure CSS scroll timeline; static
 * (final) position without support or under reduced motion. `speed` 0.2 means +/-20px.
 */
export default function Parallax({ children, speed = 0.2 }: { children: ReactNode; speed?: number }) {
  const style = { "--motion-parallax-distance": `${speed * 100}px` } as CSSProperties;
  return (
    <div className="motion-parallax" style={style}>
      {children}
    </div>
  );
}
