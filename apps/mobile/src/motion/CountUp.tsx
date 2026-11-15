import React, { useEffect, useState } from 'react';
import { Text, TextProps } from 'react-native';
import { motion } from '../generated/tokens';
import { countUpValue, shouldAnimate } from './logic';
import { useReducedMotion } from './useReducedMotion';

const defaultFormat = (n: number) => String(Math.round(n));

/**
 * Renders the FINAL formatted value initially; after mount, unless reduced motion, counts up
 * from 0 once. Cancels its frame loop on unmount.
 */
export function CountUp({
  to,
  durationMs = motion.duration.slow,
  format = defaultFormat,
  ...textProps
}: {
  to: number;
  durationMs?: number;
  format?: (n: number) => string;
} & TextProps) {
  const reduced = useReducedMotion();
  const [frame, setFrame] = useState<{ to: number; value: number } | null>(null);

  useEffect(() => {
    if (!shouldAnimate(reduced) || durationMs <= 0) return;
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

  const value = shouldAnimate(reduced) && frame && frame.to === to ? frame.value : to;
  return <Text {...textProps}>{format(value)}</Text>;
}
