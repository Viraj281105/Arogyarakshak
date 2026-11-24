import React from 'react';
import { ActivityIndicator, StyleSheet, Text, View, ViewStyle } from 'react-native';
import { useTheme, textStyles, textStyleFor } from '../../theme';
import { useReducedMotion } from '../../motion';
import { SkeletonText } from '../Skeleton';
import { Icon, type IconName } from './Icon';
import { stateSwatch, type StateKind } from './tones';

/**
 * Panel states every Wave 3 screen must have (plan section 4): loading, empty (components/EmptyState),
 * error, partial, insufficient evidence and, on mobile, offline. Each says what happened in words;
 * glyphs are decorative. Actions are passed in (e.g. a Button), so the caller decides whether a
 * retry exists. Same names and required props as the web primitives.
 */

interface PanelProps {
  kind: StateKind;
  icon: IconName;
  title: string;
  body?: string;
  role: 'alert' | 'summary';
  live: 'polite' | 'assertive';
  children?: React.ReactNode;
  action?: React.ReactNode;
  style?: ViewStyle;
}

function StatePanel({ kind, icon, title, body, role, live, children, action, style }: PanelProps) {
  const { colors, spacing, radii } = useTheme();
  const s = stateSwatch(colors, kind);
  return (
    <View
      accessibilityRole={role}
      accessibilityLiveRegion={live}
      testID={`state-${kind}`}
      style={[
        styles.panel,
        {
          backgroundColor: s.bg,
          borderColor: s.border,
          borderLeftColor: s.accent,
          borderRadius: radii.md,
          padding: spacing.md,
        },
        style,
      ]}
    >
      <Icon name={icon} size={20} color={s.accent} style={{ marginRight: spacing.sm, marginTop: 2 }} />
      <View style={styles.text}>
        <Text accessibilityRole="header" style={[textStyleFor(textStyles.label, title, '600'), { color: s.title }]}>
          {title}
        </Text>
        {body ? (
          <Text style={[textStyleFor(textStyles.bodySmall, body, '400'), { color: s.body, marginTop: 2 }]}>{body}</Text>
        ) : null}
        {children}
        {action ? <View style={{ marginTop: spacing.sm, alignSelf: 'flex-start' }}>{action}</View> : null}
      </View>
    </View>
  );
}

/** Spinner (or, under reduced motion, a static marker) plus words; optional skeleton lines. */
export function LoadingState({ label = 'Loading…', lines = 0, style }: { label?: string; lines?: number; style?: ViewStyle }) {
  const { colors, spacing, radii } = useTheme();
  const reduced = useReducedMotion();
  const s = stateSwatch(colors, 'loading');
  return (
    <View
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel={label}
      accessibilityState={{ busy: true }}
      accessibilityLiveRegion="polite"
      testID="state-loading"
      style={[styles.loading, { backgroundColor: s.bg, borderColor: s.border, borderRadius: radii.md, padding: spacing.md }, style]}
    >
      <View style={styles.loadingRow}>
        {reduced ? (
          <Icon name={{ glyph: '…' }} size={20} color={s.accent} />
        ) : (
          <ActivityIndicator size="small" color={s.accent} />
        )}
        <Text style={[textStyleFor(textStyles.bodySmall, label, '400'), { color: s.body, marginLeft: spacing.sm }]}>{label}</Text>
      </View>
      {lines > 0 ? <SkeletonText lines={lines} style={{ marginTop: spacing.md, alignSelf: 'stretch' }} /> : null}
    </View>
  );
}

export function ErrorState({
  title = 'Something went wrong',
  body,
  children,
  action,
  style,
}: {
  title?: string;
  body?: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
  style?: ViewStyle;
}) {
  return (
    <StatePanel kind="error" icon={{ action: 'error' }} title={title} body={body} role="alert" live="assertive" action={action} style={style}>
      {children}
    </StatePanel>
  );
}

/** Some parts of a result are present and some are not; lists what is missing so it is not mistaken for complete. */
export function PartialResultState({
  title = 'Partial result',
  body,
  missing,
  children,
  style,
}: {
  title?: string;
  body?: string;
  /** What could not be produced, in plain words. Required: a partial state must say what is partial. */
  missing: readonly string[];
  children?: React.ReactNode;
  style?: ViewStyle;
}) {
  const { colors, spacing } = useTheme();
  return (
    <StatePanel kind="partial" icon={{ glyph: '◑' }} title={title} body={body} role="summary" live="polite" style={style}>
      {children}
      <Text style={[textStyles.labelSmall, { color: colors.textSecondary, marginTop: spacing.xs }]}>Not available:</Text>
      {missing.map((m) => (
        <Text key={m} style={[textStyleFor(textStyles.bodySmall, m, '400'), { color: colors.textSecondary }]}>
          {'•'} {m}
        </Text>
      ))}
    </StatePanel>
  );
}

/** The engines did not have enough evidence to conclude. Says so instead of showing a guess. */
export function InsufficientEvidenceState({
  title = 'Not enough evidence to conclude',
  reason,
  children,
  style,
}: {
  title?: string;
  /** Why, in plain words (e.g. "No CGHS row matches this line"). */
  reason: string;
  children?: React.ReactNode;
  style?: ViewStyle;
}) {
  const { colors, spacing } = useTheme();
  return (
    <StatePanel kind="insufficient" icon={{ evidence: 'insufficient-evidence' }} title={title} body={reason} role="summary" live="polite" style={style}>
      {children}
      <Text style={[textStyles.caption, { color: colors.textMuted, marginTop: spacing.xs }]}>
        No figure is shown, and nothing is guessed.
      </Text>
    </StatePanel>
  );
}

/** Mobile only: the action needs the server and the phone is offline. */
export function OfflineState({
  title = 'You are offline',
  body = 'This needs a connection to the ArogyaRakshak server. Check your connection and try again.',
  action,
  style,
}: {
  title?: string;
  body?: string;
  action?: React.ReactNode;
  style?: ViewStyle;
}) {
  return <StatePanel kind="offline" icon={{ action: 'offline' }} title={title} body={body} role="summary" live="polite" action={action} style={style} />;
}

const styles = StyleSheet.create({
  panel: { flexDirection: 'row', alignItems: 'flex-start', borderWidth: 1, borderLeftWidth: 4, marginVertical: 6 },
  text: { flex: 1 },
  loading: { borderWidth: 1, marginVertical: 6 },
  loadingRow: { flexDirection: 'row', alignItems: 'center', minHeight: 24 },
});
