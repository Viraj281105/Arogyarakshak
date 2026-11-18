import React, { useState } from 'react';
import { Pressable as RNPressable, PressableProps, StyleSheet, ViewStyle } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';
import { motion } from '../generated/tokens';
import { tap } from './haptics';
import { shouldAnimate, splitTransform, withPressScale } from './logic';
import { useReducedMotion } from './useReducedMotion';

const PRESSED_SCALE = 0.97;
const AnimatedPressable = Animated.createAnimatedComponent(RNPressable);

/**
 * RN Pressable with a 0.97 press scale and a light haptic. The scale is animated on the Pressable
 * itself, so the caller's style (layout, background, border) lands on exactly one element and the
 * hit area is untouched. A caller-supplied `transform` is kept: the scale is appended to it.
 */
export function Pressable({ children, style, onPressIn, onPressOut, ...rest }: PressableProps) {
  const reduced = useReducedMotion();
  const [pressed, setPressed] = useState(false);
  const scale = useSharedValue(1);
  const state = { pressed };
  const flat = StyleSheet.flatten(typeof style === 'function' ? style(state) : style) as ViewStyle | undefined;
  const { transform: base, rest: resolved } = splitTransform(flat);
  const animatedStyle = useAnimatedStyle(
    () => ({ transform: withPressScale(base, scale.value) }) as unknown as ViewStyle,
  );

  return (
    <AnimatedPressable
      {...rest}
      style={[resolved, animatedStyle]}
      onPressIn={(e) => {
        setPressed(true);
        if (shouldAnimate(reduced)) {
          scale.value = withTiming(PRESSED_SCALE, { duration: motion.duration.fast });
        }
        void tap('light');
        onPressIn?.(e);
      }}
      onPressOut={(e) => {
        setPressed(false);
        scale.value = withTiming(1, { duration: motion.duration.fast });
        onPressOut?.(e);
      }}
    >
      {typeof children === 'function' ? children(state as never) : children}
    </AnimatedPressable>
  );
}
