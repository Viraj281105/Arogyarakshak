import React from 'react';
import { Pressable as RNPressable, PressableProps } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';
import { motion } from '../generated/tokens';
import { tap } from './haptics';
import { shouldAnimate } from './logic';
import { useReducedMotion } from './useReducedMotion';

const PRESSED_SCALE = 0.97;

/**
 * RN Pressable with a 0.97 press scale and a light haptic. The scale lives on an inner view, so
 * the Pressable's own hit area (and any minHeight/hitSlop passed in) is untouched.
 */
export function Pressable({ children, onPressIn, onPressOut, ...rest }: PressableProps) {
  const reduced = useReducedMotion();
  const scale = useSharedValue(1);
  const style = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));

  return (
    <RNPressable
      {...rest}
      onPressIn={(e) => {
        if (shouldAnimate(reduced)) {
          scale.value = withTiming(PRESSED_SCALE, { duration: motion.duration.fast });
        }
        void tap('light');
        onPressIn?.(e);
      }}
      onPressOut={(e) => {
        scale.value = withTiming(1, { duration: motion.duration.fast });
        onPressOut?.(e);
      }}
    >
      {(state) => (
        <Animated.View style={style}>
          {typeof children === 'function' ? children(state) : children}
        </Animated.View>
      )}
    </RNPressable>
  );
}
