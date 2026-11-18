import React, { useMemo } from 'react';
import { Animated } from 'react-native';
import { shouldAnimate } from './logic';
import { useReducedMotion } from './useReducedMotion';

/**
 * Scroll-linked translate: offset = scrollY * (speed - 1). Static under reduced motion.
 * `scrollY` is an Animated.Value fed by the scroll view, e.g.
 * `onScroll={Animated.event([{ nativeEvent: { contentOffset: { y: scrollY } } }], { useNativeDriver: NATIVE_DRIVER })}`
 * (NATIVE_DRIVER from src/motion/driver: react-native-web has no native driver).
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
  const animate = shouldAnimate(reduced);
  const translateY = useMemo(
    () => (animate ? Animated.multiply(scrollY, speed - 1) : 0),
    [animate, scrollY, speed],
  );

  return <Animated.View style={{ transform: [{ translateY }] }}>{children}</Animated.View>;
}
