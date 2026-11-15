import React, { useEffect } from 'react';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withTiming,
} from 'react-native-reanimated';
import { motion } from '../generated/tokens';
import { STANDARD_BEZIER, shouldAnimate } from './logic';
import { useReducedMotion } from './useReducedMotion';

const OFFSET_Y = 12;
const EASE = Easing.bezier(...STANDARD_BEZIER);

/** Fade + 12px rise on mount. Final state immediately under reduced motion. */
export function Reveal({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const reduced = useReducedMotion();
  const progress = useSharedValue(shouldAnimate(reduced) ? 0 : 1);

  useEffect(() => {
    if (!shouldAnimate(reduced)) {
      progress.value = 1;
      return;
    }
    progress.value = 0;
    progress.value = withDelay(delay, withTiming(1, { duration: motion.duration.base, easing: EASE }));
  }, [reduced, delay, progress]);

  const style = useAnimatedStyle(() => ({
    opacity: progress.value,
    transform: [{ translateY: (1 - progress.value) * OFFSET_Y }],
  }));

  return <Animated.View style={style}>{children}</Animated.View>;
}
