import React, { useRef, useState } from 'react';
import { Animated, Pressable as RNPressable, PressableProps, StyleSheet, ViewStyle } from 'react-native';
import { motion } from '../generated/tokens';
import { tap } from './haptics';
import { shouldAnimate, splitTransform, withPressScale } from './logic';
import { NATIVE_DRIVER } from './driver';
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
  const scale = useRef(new Animated.Value(1)).current;
  const state = { pressed };
  const flat = StyleSheet.flatten(typeof style === 'function' ? style(state) : style) as ViewStyle | undefined;
  const { transform: base, rest: resolved } = splitTransform(flat);
  const animatedStyle = { transform: withPressScale(base, scale) } as unknown as ViewStyle;

  const to = (value: number) =>
    Animated.timing(scale, { toValue: value, duration: motion.duration.fast, useNativeDriver: NATIVE_DRIVER }).start();

  return (
    <AnimatedPressable
      {...rest}
      style={[resolved, animatedStyle]}
      onPressIn={(e) => {
        setPressed(true);
        if (shouldAnimate(reduced)) to(PRESSED_SCALE);
        void tap('light');
        onPressIn?.(e);
      }}
      onPressOut={(e) => {
        setPressed(false);
        to(1);
        onPressOut?.(e);
      }}
    >
      {typeof children === 'function' ? children(state as never) : children}
    </AnimatedPressable>
  );
}
