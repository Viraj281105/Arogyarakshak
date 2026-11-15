import React from 'react';
import Animated, { SharedValue, useAnimatedStyle } from 'react-native-reanimated';
import { shouldAnimate } from './logic';
import { useReducedMotion } from './useReducedMotion';

/** Scroll-linked translate: offset = scrollY * (speed - 1). Static under reduced motion. */
export function Parallax({
  children,
  speed = 0.9,
  scrollY,
}: {
  children: React.ReactNode;
  speed?: number;
  scrollY: SharedValue<number>;
}) {
  const reduced = useReducedMotion();
  const animate = shouldAnimate(reduced);

  const style = useAnimatedStyle(() => ({
    transform: [{ translateY: animate ? scrollY.value * (speed - 1) : 0 }],
  }));

  return <Animated.View style={style}>{children}</Animated.View>;
}
