import React from 'react';
import { StyleSheet, Text, View, ViewStyle } from 'react-native';
import { useTheme, textStyles } from '../theme';
import { Reveal } from '../motion';
import { Button } from './Button';

export interface EmptyStateProps {
  title: string;
  body?: string;
  /** A glyph or small element shown above the title. */
  icon?: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  style?: ViewStyle;
}

/** Centered "nothing here yet" block with an optional single action. Reveals once on mount. */
export const EmptyState: React.FC<EmptyStateProps> = ({ title, body, icon, actionLabel, onAction, style }) => {
  const { colors, spacing } = useTheme();
  return (
    <Reveal>
      <View style={[styles.container, { padding: spacing.lg }, style]}>
        {icon != null && (
          <View style={{ marginBottom: spacing.sm }}>
            {typeof icon === 'string' ? <Text style={styles.glyph}>{icon}</Text> : icon}
          </View>
        )}
        <Text accessibilityRole="header" style={[textStyles.title, styles.center, { color: colors.textPrimary }]}>
          {title}
        </Text>
        {body ? (
          <Text
            style={[textStyles.bodySmall, styles.center, { color: colors.textSecondary, marginTop: spacing.xs }]}
          >
            {body}
          </Text>
        ) : null}
        {actionLabel && onAction ? (
          <Button title={actionLabel} onPress={onAction} variant="secondary" style={{ marginTop: spacing.md }} />
        ) : null}
      </View>
    </Reveal>
  );
};

const styles = StyleSheet.create({
  container: { alignItems: 'center', justifyContent: 'center' },
  center: { textAlign: 'center' },
  glyph: { fontSize: 32, lineHeight: 40 },
});
