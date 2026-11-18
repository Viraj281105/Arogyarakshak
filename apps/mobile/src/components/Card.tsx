import React, { ReactNode } from 'react';
import { View, StyleSheet, ViewStyle, AccessibilityProps } from 'react-native';
import { useTheme } from '../theme';
import { Pressable, Reveal } from '../motion';

export interface CardProps extends AccessibilityProps {
  children: ReactNode;
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

  const cardStyle = [
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
  ];

  const body = onPress ? (
    <Pressable onPress={onPress} accessibilityRole="button" {...a11y} style={cardStyle}>
      {children}
    </Pressable>
  ) : (
    <View {...a11y} style={cardStyle}>
      {children}
    </View>
  );

  return reveal ? <Reveal delay={revealDelay}>{body}</Reveal> : body;
};

const styles = StyleSheet.create({
  cardBase: {
    borderWidth: 1,
    marginVertical: 6,
  },
});
