import React from 'react';
import {
  Text,
  StyleSheet,
  ActivityIndicator,
  ViewStyle,
  TextStyle,
  AccessibilityProps,
} from 'react-native';
import { useTheme, fontFor } from '../theme';
import { Pressable } from '../motion';
import { buttonSwatch, type ButtonVariant } from './ui/tones';

export interface ButtonProps extends AccessibilityProps {
  title: string;
  onPress: () => void;
  variant?: ButtonVariant;
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

  // Colours come from tones.ts, which the contrast test checks in both themes. Filled variants use
  // the action pair (textOnAction is navy in the dark theme): white on dark brandCyan was 2.04:1.
  const swatch = buttonSwatch(colors, variant, disabled);
  const getBackgroundColor = () => swatch.bg ?? 'transparent';
  const getTextColor = () => swatch.fg;
  const getBorderColor = () => swatch.border ?? 'transparent';
  const bordered = swatch.border !== null;

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
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      accessible={true}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel || title}
      accessibilityHint={accessibilityHint}
      accessibilityState={{ disabled: disabled || loading, busy: loading }}
      style={({ pressed }) => [
        styles.buttonBase,
        {
          backgroundColor: getBackgroundColor(),
          borderColor: getBorderColor(),
          borderWidth: bordered ? 1 : 0,
          borderRadius: radii.md,
          minHeight: spacing.minTouchTarget, // Enforces 44px WCAG minimum
          minWidth: spacing.minTouchTarget,
          ...getPadding(),
        },
        pressed && styles.pressed,
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
                ...fontFor(title, 'sans', '600'),
                marginLeft: icon ? spacing.xs : 0,
              },
              textStyle,
            ]}
          >
            {title}
          </Text>
        </>
      )}
    </Pressable>
  );
};

const styles = StyleSheet.create({
  buttonBase: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: {
    opacity: 0.85,
  },
  spinner: {
    marginVertical: 2,
  },
  textBase: {
    textAlign: 'center',
  },
});
