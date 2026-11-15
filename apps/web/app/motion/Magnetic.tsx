"use client";

import { useEffect, type PointerEvent, type ReactNode } from "react";
import { LazyMotion, m, useMotionValue, useSpring } from "motion/react";
import { useReducedMotion } from "./useReducedMotion";

const loadFeatures = () => import("./motionFeatures").then((mod) => mod.default);

/**
 * Pulls its child toward the pointer. JS-driven (Motion springs, features loaded lazily).
 * Inert for touch pointers and under reduced motion; markup is identical either way.
 */
export default function Magnetic({ children, strength = 0.3 }: { children: ReactNode; strength?: number }) {
  const reduced = useReducedMotion();
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, { stiffness: 220, damping: 16, mass: 0.3 });
  const springY = useSpring(y, { stiffness: 220, damping: 16, mass: 0.3 });

  useEffect(() => {
    if (reduced) {
      x.set(0);
      y.set(0);
    }
  }, [reduced, x, y]);

  const onMove = (e: PointerEvent<HTMLDivElement>) => {
    if (reduced || e.pointerType === "touch") return;
    const r = e.currentTarget.getBoundingClientRect();
    x.set((e.clientX - (r.left + r.width / 2)) * strength);
    y.set((e.clientY - (r.top + r.height / 2)) * strength);
  };
  const onLeave = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <LazyMotion features={loadFeatures} strict>
      <m.div
        className="motion-magnetic"
        style={{ x: springX, y: springY, display: "inline-block" }}
        onPointerMove={onMove}
        onPointerLeave={onLeave}
      >
        {children}
      </m.div>
    </LazyMotion>
  );
}
