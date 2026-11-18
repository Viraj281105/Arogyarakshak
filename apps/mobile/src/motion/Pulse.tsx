import React, { useEffect } from 'react';
import { StyleProp, ViewStyle } from 'react-native';
import Animated, {
  cancelAnimation,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
import { motion } from '../generated/tokens';
import { PULSE_MAX_OPACITY, PULSE_MIN_OPACITY, shouldAnimate } from './logic';
import { useReducedMotion } from './useReducedMotion';

/**
 * Loading pulse (opacity loop between PULSE_MIN_OPACITY and PULSE_MAX_OPACITY) for skeletons.
 * Static at the max opacity under reduced motion. The loop is cancelled on unmount.
 */
export function Pulse({ children, style }: { children?: React.ReactNode; style?: StyleProp<ViewStyle> }) {
  const reduced = useReducedMotion();
  const opacity = useSharedValue(PULSE_MAX_OPACITY);

  useEffect(() => {
    if (!shouldAnimate(reduced)) {
      cancelAnimation(opacity);
      opacity.value = PULSE_MAX_OPACITY;
      return;
    }
    opacity.value = withRepeat(withTiming(PULSE_MIN_OPACITY, { duration: motion.duration.slow * 2 }), -1, true);
    return () => cancelAnimation(opacity);
  }, [reduced, opacity]);

  const animated = useAnimatedStyle(() => ({ opacity: opacity.value }));

  return <Animated.View style={[style, animated]}>{children}</Animated.View>;
}
