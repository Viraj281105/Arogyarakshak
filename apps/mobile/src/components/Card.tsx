import React, { ReactNode } from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { useTheme } from '../theme';

export interface CardProps {
  children: ReactNode;
  style?: ViewStyle;
  elevated?: boolean;
}

export const Card: React.FC<CardProps> = ({ children, style, elevated = false }) => {
  const { colors, spacing, radii, isDark } = useTheme();

  return (
    <View
      style={[
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
      ]}
    >
      {children}
    </View>
  );
};

const styles = StyleSheet.create({
  cardBase: {
    borderWidth: 1,
    marginVertical: 6,
  },
});
