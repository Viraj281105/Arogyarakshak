import React from 'react';
import { DimensionValue, StyleSheet, View, ViewStyle } from 'react-native';
import { useTheme } from '../theme';
import { Pulse } from '../motion';

export interface SkeletonProps {
  width?: DimensionValue;
  height?: number;
  radius?: number;
  style?: ViewStyle;
}

/** Loading placeholder block. Pulses via the motion system; static under reduced motion. */
export const Skeleton: React.FC<SkeletonProps> = ({ width = '100%', height = 14, radius, style }) => {
  const { colors, radii } = useTheme();
  return (
    <Pulse
      style={[
        { width, height, borderRadius: radius ?? radii.sm, backgroundColor: colors.bgSurfaceElevated },
        style,
      ]}
    />
  );
};

/** A few text-line placeholders; the last line is shorter, like a paragraph. */
export const SkeletonText: React.FC<{ lines?: number; style?: ViewStyle }> = ({ lines = 3, style }) => {
  const { spacing } = useTheme();
  return (
    <View
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel="Loading"
      accessibilityState={{ busy: true }}
      style={style}
    >
      {Array.from({ length: Math.max(1, lines) }, (_, i) => (
        <Skeleton
          key={i}
          width={i === lines - 1 && lines > 1 ? '60%' : '100%'}
          style={i > 0 ? { marginTop: spacing.sm } : undefined}
        />
      ))}
    </View>
  );
};

/** Card-shaped placeholder (title line + body lines) matching Card padding and radius. */
export const SkeletonCard: React.FC<{ lines?: number; style?: ViewStyle }> = ({ lines = 3, style }) => {
  const { colors, spacing, radii } = useTheme();
  return (
    <View
      style={[
        styles.card,
        { backgroundColor: colors.bgSurface, borderColor: colors.borderSubtle, borderRadius: radii.lg, padding: spacing.md },
        style,
      ]}
    >
      <Skeleton width="45%" height={18} style={{ marginBottom: spacing.md }} />
      <SkeletonText lines={lines} />
    </View>
  );
};

const styles = StyleSheet.create({
  card: { borderWidth: 1, marginVertical: 6 },
});
