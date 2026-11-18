import React, { useEffect, useRef } from 'react';
import { Animated, StyleProp, ViewStyle } from 'react-native';
import { motion } from '../generated/tokens';
import { revealAction, shouldAnimate } from './logic';
import { NATIVE_DRIVER, STANDARD_EASING } from './driver';
import { useReducedMotion } from './useReducedMotion';

const OFFSET_Y = 12;

/**
 * Fade + 12px rise on mount, at most once. Final state immediately under reduced motion (or while
 * the preference is unknown); a late prime of the preference does not replay a mounted Reveal.
 */
export function Reveal({
  children,
  delay = 0,
  style,
}: {
  children: React.ReactNode;
  delay?: number;
  style?: StyleProp<ViewStyle>;
}) {
  const reduced = useReducedMotion();
  const started = useRef(false);
  const progress = useRef(new Animated.Value(shouldAnimate(reduced) ? 0 : 1)).current;

  useEffect(() => {
    const action = revealAction(started.current, reduced);
    started.current = true;
    if (action === 'final') {
      progress.stopAnimation();
      progress.setValue(1);
    } else if (action === 'animate') {
      progress.setValue(0);
      Animated.timing(progress, {
        toValue: 1,
        delay,
        duration: motion.duration.base,
        easing: STANDARD_EASING,
        useNativeDriver: NATIVE_DRIVER,
      }).start();
    }
  }, [reduced, delay, progress]);

  useEffect(() => () => progress.stopAnimation(), [progress]);

  const translateY = progress.interpolate({ inputRange: [0, 1], outputRange: [OFFSET_Y, 0] });

  return <Animated.View style={[style, { opacity: progress, transform: [{ translateY }] }]}>{children}</Animated.View>;
}
