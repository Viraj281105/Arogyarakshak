import React from 'react';
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
  ViewStyle,
  TextStyle,
  AccessibilityProps,
} from 'react-native';
import { useTheme } from '../theme';

export interface ButtonProps extends AccessibilityProps {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  disabled?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  title,
  onPress,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  style,
  textStyle,
  icon,
  accessibilityLabel,
  accessibilityHint,
  ...rest
}) => {
  const { colors, spacing, radii, typography } = useTheme();

  const getBackgroundColor = () => {
    if (disabled) return colors.borderMedium;
    switch (variant) {
      case 'primary':
        return colors.brandCyan;
      case 'secondary':
        return colors.bgSurfaceElevated;
      case 'outline':
      case 'ghost':
        return 'transparent';
      case 'danger':
        return colors.statusDanger;
      default:
        return colors.brandCyan;
    }
  };

  const getTextColor = () => {
    if (disabled) return colors.textMuted;
    switch (variant) {
      case 'primary':
      case 'danger':
        return '#ffffff';
      case 'secondary':
      case 'ghost':
        return colors.textPrimary;
      case 'outline':
        return colors.brandCyan;
      default:
        return '#ffffff';
    }
  };

  const getBorderColor = () => {
    if (disabled) return 'transparent';
    switch (variant) {
      case 'outline':
        return colors.brandCyan;
      case 'secondary':
        return colors.borderMedium;
      default:
        return 'transparent';
    }
  };

  const getPadding = () => {
    switch (size) {
      case 'sm':
        return { paddingVertical: spacing.xs, paddingHorizontal: spacing.sm };
      case 'lg':
        return { paddingVertical: spacing.md, paddingHorizontal: spacing.lg };
      case 'md':
      default:
        return { paddingVertical: spacing.sm, paddingHorizontal: spacing.md };
    }
  };

  return (
    <TouchableOpacity
      activeOpacity={0.75}
      onPress={onPress}
      disabled={disabled || loading}
      accessible={true}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel || title}
      accessibilityHint={accessibilityHint}
      accessibilityState={{ disabled: disabled || loading, busy: loading }}
      style={[
        styles.buttonBase,
        {
          backgroundColor: getBackgroundColor(),
          borderColor: getBorderColor(),
          borderWidth: variant === 'outline' || variant === 'secondary' ? 1 : 0,
          borderRadius: radii.md,
          minHeight: spacing.minTouchTarget, // Enforces 44px WCAG minimum
          minWidth: spacing.minTouchTarget,
          ...getPadding(),
        },
        style,
      ]}
      {...rest}
    >
      {loading ? (
        <ActivityIndicator
          size="small"
          color={getTextColor()}
          style={styles.spinner}
        />
      ) : (
        <>
          {icon}
          <Text
            style={[
              styles.textBase,
              {
                color: getTextColor(),
                fontSize: size === 'sm' ? typography.sizes.sm : typography.sizes.md,
                fontWeight: typography.weights.semibold,
                marginLeft: icon ? spacing.xs : 0,
              },
              textStyle,
            ]}
          >
            {title}
          </Text>
        </>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  buttonBase: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  spinner: {
    marginVertical: 2,
  },
  textBase: {
    textAlign: 'center',
  },
});
