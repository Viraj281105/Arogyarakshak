import React, { useEffect } from 'react';
import { StyleProp, ViewStyle } from 'react-native';
import Animated, { Easing, useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';
import { motion } from '../generated/tokens';
import { STANDARD_BEZIER, shouldAnimate } from './logic';
import { useReducedMotion } from './useReducedMotion';

const EASE = Easing.bezier(...STANDARD_BEZIER);

/**
 * Absolutely positioned element that slides horizontally to `x` (e.g. the active-tab pill).
 * Jumps without animation under reduced motion or while the preference is unknown.
 */
export function SlidingIndicator({
  x,
  width,
  style,
}: {
  x: number;
  width: number;
  style?: StyleProp<ViewStyle>;
}) {
  const reduced = useReducedMotion();
  const tx = useSharedValue(x);

  useEffect(() => {
    tx.value = shouldAnimate(reduced)
      ? withTiming(x, { duration: motion.duration.base, easing: EASE })
      : x;
  }, [x, reduced, tx]);

  const animated = useAnimatedStyle(() => ({ transform: [{ translateX: tx.value }] }));

  return (
    <Animated.View
      pointerEvents="none"
      style={[{ position: 'absolute', left: 0, width }, style, animated]}
    />
  );
}
