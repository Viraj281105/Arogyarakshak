import React from 'react';
import { StyleSheet, Text, View, ViewStyle } from 'react-native';
import { useTheme, textStyles, textStyleFor } from '../theme';
import { Reveal } from '../motion';
import { Button } from './Button';
import { Icon } from './ui/Icon';

export interface EmptyStateProps {
  title: string;
  body?: string;
  /** A glyph string or small element shown above the title. Defaults to the "cases" glyph. */
  icon?: React.ReactNode;
  /** Shorthand for a single secondary Button. */
  actionLabel?: string;
  onAction?: () => void;
  /** Any action element instead of the shorthand (same as the web EmptyState `action`). */
  action?: React.ReactNode;
  /** Extra content under the body. */
  children?: React.ReactNode;
  style?: ViewStyle;
}

/**
 * Centered "nothing here yet" block with an optional action. Reveals once on mount (final state
 * under reduced motion). One of the Wave 3 panel states, alongside components/ui/States.tsx.
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  body,
  icon,
  actionLabel,
  onAction,
  action,
  children,
  style,
}) => {
  const { colors, spacing } = useTheme();
  return (
    <Reveal>
      <View accessibilityRole="summary" testID="state-empty" style={[styles.container, { padding: spacing.lg }, style]}>
        <View style={{ marginBottom: spacing.sm }}>
          {icon == null ? (
            <Icon name={{ action: 'cases' }} size={32} />
          ) : typeof icon === 'string' ? (
            <Icon name={{ glyph: icon }} size={32} color={colors.textMuted} />
          ) : (
            icon
          )}
        </View>
        <Text accessibilityRole="header" style={[textStyleFor(textStyles.title, title, '700'), styles.center, { color: colors.textPrimary }]}>
          {title}
        </Text>
        {body ? (
          <Text
            style={[textStyleFor(textStyles.bodySmall, body, '400'), styles.center, { color: colors.textSecondary, marginTop: spacing.xs }]}
          >
            {body}
          </Text>
        ) : null}
        {children}
        {action ? (
          <View style={{ marginTop: spacing.md }}>{action}</View>
        ) : actionLabel && onAction ? (
          <Button title={actionLabel} onPress={onAction} variant="secondary" style={{ marginTop: spacing.md }} />
        ) : null}
      </View>
    </Reveal>
  );
};

const styles = StyleSheet.create({
  container: { alignItems: 'center', justifyContent: 'center' },
  center: { textAlign: 'center' },
});
