import React, { useEffect, useRef } from 'react';
import { Animated, StyleProp, ViewStyle } from 'react-native';
import { motion } from '../generated/tokens';
import { PULSE_MAX_OPACITY, PULSE_MIN_OPACITY, shouldAnimate } from './logic';
import { NATIVE_DRIVER } from './driver';
import { useReducedMotion } from './useReducedMotion';

/**
 * Loading pulse (opacity loop between PULSE_MIN_OPACITY and PULSE_MAX_OPACITY) for skeletons.
 * Static at the max opacity under reduced motion. The loop is stopped on unmount.
 */
export function Pulse({ children, style }: { children?: React.ReactNode; style?: StyleProp<ViewStyle> }) {
  const reduced = useReducedMotion();
  const opacity = useRef(new Animated.Value(PULSE_MAX_OPACITY)).current;

  useEffect(() => {
    if (!shouldAnimate(reduced)) {
      opacity.stopAnimation();
      opacity.setValue(PULSE_MAX_OPACITY);
      return;
    }
    const step = (toValue: number) =>
      Animated.timing(opacity, { toValue, duration: motion.duration.slow * 2, useNativeDriver: NATIVE_DRIVER });
    const loop = Animated.loop(Animated.sequence([step(PULSE_MIN_OPACITY), step(PULSE_MAX_OPACITY)]));
    loop.start();
    return () => loop.stop();
  }, [reduced, opacity]);

  return <Animated.View style={[style, { opacity }]}>{children}</Animated.View>;
}
