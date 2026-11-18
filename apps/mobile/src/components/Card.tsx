import React, { ReactNode } from 'react';
import { View, StyleSheet, ViewStyle, AccessibilityProps } from 'react-native';
import { useTheme } from '../theme';
import { Pressable, Reveal } from '../motion';
import { splitLayoutStyle } from '../shell/logic';

export interface CardProps extends AccessibilityProps {
  children: ReactNode;
  /**
   * Card style. With `reveal` on, layout keys (flex*, width/height and their min/max, alignSelf,
   * margin*, position and offsets, zIndex: see LAYOUT_STYLE_KEYS) are applied to the Reveal wrapper
   * so the card positions exactly as an unwrapped View would; everything else styles the card.
   */
  style?: ViewStyle;
  elevated?: boolean;
  /** Fade + rise on mount via the motion system (once; static under reduced motion). Default true. */
  reveal?: boolean;
  /** Delay for the reveal, e.g. to stagger a short list of cards. */
  revealDelay?: number;
  /** Makes the whole card a motion Pressable (press scale + light haptic). */
  onPress?: () => void;
}

export const Card: React.FC<CardProps> = ({
  children,
  style,
  elevated = false,
  reveal = true,
  revealDelay = 0,
  onPress,
  ...a11y
}) => {
  const { colors, spacing, radii, isDark } = useTheme();

  const flat = (StyleSheet.flatten([
    styles.cardBase,
    {
      backgroundColor: elevated ? colors.bgSurfaceElevated : colors.bgSurface,
      borderColor: isDark ? 'rgba(255, 255, 255, 0.1)' : colors.borderSubtle,
      borderRadius: radii.lg,
      padding: spacing.md,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: isDark ? 0.45 : 0.08,
      shadowRadius: 12,
      elevation: isDark ? 4 : 2,
    },
    style,
  ]) ?? {}) as Record<string, unknown>;

  const { outer, inner } = reveal ? splitLayoutStyle(flat) : { outer: {}, inner: flat };
  const cardStyle = inner as ViewStyle;

  const body = onPress ? (
    <Pressable onPress={onPress} accessibilityRole="button" {...a11y} style={cardStyle}>
      {children}
    </Pressable>
  ) : (
    <View {...a11y} style={cardStyle}>
      {children}
    </View>
  );

  return reveal ? (
    <Reveal delay={revealDelay} style={outer as ViewStyle}>
      {body}
    </Reveal>
  ) : (
    body
  );
};

const styles = StyleSheet.create({
  cardBase: {
    borderWidth: 1,
    marginVertical: 6,
  },
});
