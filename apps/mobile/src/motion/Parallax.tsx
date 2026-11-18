import React from 'react';
import { Animated } from 'react-native';
import { shouldAnimate } from './logic';
import { useReducedMotion } from './useReducedMotion';

/**
 * Scroll-linked translate: offset = scrollY * (speed - 1). Static under reduced motion.
 * `scrollY` is an Animated.Value fed by the scroll view, e.g.
 * `onScroll={Animated.event([{ nativeEvent: { contentOffset: { y: scrollY } } }], { useNativeDriver: true })}`.
 */
export function Parallax({
  children,
  speed = 0.9,
  scrollY,
}: {
  children: React.ReactNode;
  speed?: number;
  scrollY: Animated.Value;
}) {
  const reduced = useReducedMotion();
  const translateY = shouldAnimate(reduced) ? Animated.multiply(scrollY, speed - 1) : 0;

  return <Animated.View style={{ transform: [{ translateY }] }}>{children}</Animated.View>;
}
