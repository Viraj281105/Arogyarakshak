import React from 'react';
import { View, Text, StyleSheet, ViewStyle, TextStyle } from 'react-native';
import { useTheme } from '../theme';

export interface BadgeProps {
  label: string;
  variant?: 'info' | 'success' | 'warning' | 'danger' | 'brand';
  style?: ViewStyle;
  textStyle?: TextStyle;
}

export const Badge: React.FC<BadgeProps> = ({
  label,
  variant = 'brand',
  style,
  textStyle,
}) => {
  const { colors, spacing, radii, typography } = useTheme();

  const getColors = () => {
    switch (variant) {
      case 'success':
        return { bg: 'rgba(16, 185, 129, 0.15)', text: colors.statusSuccess };
      case 'warning':
        return { bg: 'rgba(245, 158, 11, 0.15)', text: colors.statusWarning };
      case 'danger':
        return { bg: 'rgba(239, 68, 68, 0.15)', text: colors.statusDanger };
      case 'info':
        return { bg: 'rgba(59, 130, 246, 0.15)', text: colors.statusInfo };
      case 'brand':
      default:
        return { bg: 'rgba(6, 182, 212, 0.15)', text: colors.brandCyan };
    }
  };

  const { bg, text } = getColors();

  return (
    <View
      style={[
        styles.badgeBase,
        {
          backgroundColor: bg,
          borderRadius: radii.full,
          paddingVertical: spacing.xs,
          paddingHorizontal: spacing.sm + 2,
        },
        style,
      ]}
    >
      <Text
        style={[
          styles.badgeText,
          {
            color: text,
            fontSize: typography.sizes.xs,
            fontWeight: typography.weights.semibold,
          },
          textStyle,
        ]}
      >
        {label}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  badgeBase: {
    alignSelf: 'flex-start',
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeText: {
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
});
