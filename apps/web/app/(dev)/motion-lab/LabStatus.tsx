"use client";

import { useSyncExternalStore } from "react";
import { shouldAnimate, useReducedMotion } from "../../motion/useReducedMotion";

const noop = () => () => {};

/** Dev-only readout of what the motion system currently decides. */
export default function LabStatus() {
  const reducedMotion = useReducedMotion();
  const supportsScrollTimeline = useSyncExternalStore(
    noop,
    () => typeof CSS !== "undefined" && CSS.supports("animation-timeline: view()"),
    () => false,
  );
  return (
    <p data-testid="motion-status">
      reducedMotion={String(reducedMotion)} scrollTimeline={String(supportsScrollTimeline)} animate=
      {String(shouldAnimate({ reducedMotion, supportsScrollTimeline }))}
    </p>
  );
}
