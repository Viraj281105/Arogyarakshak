import React, { useEffect, useRef } from 'react';
import { StyleProp, ViewStyle } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withTiming,
} from 'react-native-reanimated';
import { motion } from '../generated/tokens';
import { STANDARD_BEZIER, revealAction, shouldAnimate } from './logic';
import { useReducedMotion } from './useReducedMotion';

const OFFSET_Y = 12;
const EASE = Easing.bezier(...STANDARD_BEZIER);

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
  const progress = useSharedValue(shouldAnimate(reduced) ? 0 : 1);

  useEffect(() => {
    const action = revealAction(started.current, reduced);
    started.current = true;
    if (action === 'final') {
      progress.value = 1;
    } else if (action === 'animate') {
      progress.value = 0;
      progress.value = withDelay(delay, withTiming(1, { duration: motion.duration.base, easing: EASE }));
    }
  }, [reduced, delay, progress]);

  const animated = useAnimatedStyle(() => ({
    opacity: progress.value,
    transform: [{ translateY: (1 - progress.value) * OFFSET_Y }],
  }));

  return <Animated.View style={[style, animated]}>{children}</Animated.View>;
}
