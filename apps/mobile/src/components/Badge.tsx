import React from 'react';
import { View, Text, StyleSheet, ViewStyle, TextStyle } from 'react-native';
import { useTheme } from '../theme';
import { badgeSwatch, type BadgeVariant } from './ui/tones';

/** Legacy chip used by the module screens. New code: StatusBadge or EvidenceBadge (components/ui). */
export interface BadgeProps {
  label: string;
  variant?: BadgeVariant;
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

  // Status colour text on the elevated surface (tones.ts; AA-checked). The old translucent tints
  // were pre-rebrand literals whose contrast depended on whatever was underneath.
  const swatch = badgeSwatch(colors, variant);
  const bg = swatch.bg ?? undefined;
  const text = swatch.fg;

  return (
    <View
      style={[
        styles.badgeBase,
        {
          backgroundColor: bg,
          borderColor: swatch.border ?? undefined,
          borderWidth: 1,
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
