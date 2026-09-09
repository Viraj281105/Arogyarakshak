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
          borderColor: colors.borderSubtle,
          borderRadius: radii.md,
          padding: spacing.md,
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 2 },
          shadowOpacity: isDark ? 0.35 : 0.06,
          shadowRadius: 8,
          elevation: isDark ? 3 : 1,
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
