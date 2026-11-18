import React, { useEffect, useRef } from 'react';
import { Animated, StyleProp, ViewStyle } from 'react-native';
import { motion } from '../generated/tokens';
import { shouldAnimate } from './logic';
import { NATIVE_DRIVER, STANDARD_EASING } from './driver';
import { useReducedMotion } from './useReducedMotion';

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
  const tx = useRef(new Animated.Value(x)).current;

  useEffect(() => {
    if (!shouldAnimate(reduced)) {
      tx.stopAnimation();
      tx.setValue(x);
      return;
    }
    const anim = Animated.timing(tx, {
      toValue: x,
      duration: motion.duration.base,
      easing: STANDARD_EASING,
      useNativeDriver: NATIVE_DRIVER,
    });
    anim.start();
    return () => anim.stop();
  }, [x, reduced, tx]);

  return (
    <Animated.View
      pointerEvents="none"
      style={[{ position: 'absolute', left: 0, width }, style, { transform: [{ translateX: tx }] }]}
    />
  );
}
