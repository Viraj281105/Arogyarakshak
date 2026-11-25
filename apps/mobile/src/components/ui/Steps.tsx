import React from 'react';
import { StyleSheet, Text, View, ViewStyle } from 'react-native';
import { useTheme, textStyles, textStyleFor } from '../../theme';
import { Icon } from './Icon';
import { CHECKLIST_WORD, STEP_WORD, checklistSummary, stepCountText, stepState } from './logic';
import { checklistColor, stepMarkerSwatch, type ChecklistStatus } from './tones';
import { tr, msg, useTranslation } from '../../translations/tr';

/**
 * Step header for multi-step flows (e.g. DaaviSetu readiness -> template -> package): numbered
 * markers with labels and "Step n of m". Each step's state is in its accessibility label, never
 * colour-only. The caller owns navigation (Buttons in `children`). Same props as the web StepWizard.
 */
export function StepWizard({
  steps,
  current,
  label = msg('Progress'),
  children,
  style,
}: {
  steps: readonly { id: string; label: string }[];
  /** Index of the current step. */
  current: number;
  label?: string;
  children?: React.ReactNode;
  style?: ViewStyle;
}) {
  useTranslation();
  const { colors, spacing } = useTheme();
  return (
    <View style={style}>
      <View accessibilityRole="list" accessibilityLabel={tr(label)} style={styles.steps}>
        {steps.map((s, i) => {
          const state = stepState(i, current);
          const sw = stepMarkerSwatch(colors, state);
          return (
            <View
              key={s.id}
              accessible
              accessibilityLabel={tr('Step {number}: {label}, {state}', { number: i + 1, label: s.label, state: tr(STEP_WORD[state]) })}
              accessibilityState={{ selected: state === 'current' }}
              style={styles.step}
            >
              <View style={[styles.marker, { backgroundColor: sw.bg ?? undefined, borderColor: sw.border ?? undefined }]}>
                {state === 'done' ? (
                  <Icon name={{ action: 'success' }} size={14} color={sw.fg} />
                ) : (
                  <Text style={[textStyles.labelSmall, { color: sw.fg }]}>{i + 1}</Text>
                )}
              </View>
              <Text
                numberOfLines={2}
                style={[
                  textStyleFor(textStyles.caption, s.label, state === 'current' ? '700' : '500'),
                  styles.stepLabel,
                  { color: state === 'current' ? colors.textPrimary : colors.textSecondary },
                ]}
              >
                {s.label}
              </Text>
            </View>
          );
        })}
      </View>
      <Text style={[textStyles.caption, { color: colors.textSecondary, marginTop: spacing.xs }]}>
        {stepCountText(current, steps.length)}
      </Text>
      {children ? <View style={{ marginTop: spacing.md }}>{children}</View> : null}
    </View>
  );
}

const CHECK_GLYPH: Record<ChecklistStatus, string> = { done: '✓', todo: '○', blocked: '!', unknown: '◌' };

/** Read-only checklist (e.g. pre-authorisation readiness). Every item states its status in words. */
export function Checklist({
  title,
  items,
  style,
}: {
  title: string;
  items: readonly { id: string; label: string; status: ChecklistStatus; note?: string }[];
  style?: ViewStyle;
}) {
  useTranslation();
  const { colors, spacing } = useTheme();
  return (
    <View style={style}>
      <View style={styles.head}>
        <Text accessibilityRole="header" style={[textStyleFor(textStyles.label, title, '600'), { color: colors.textPrimary, flexShrink: 1 }]}>
          {title}
        </Text>
        <Text style={[textStyles.mono, { color: colors.textSecondary, marginLeft: spacing.sm }]}>{checklistSummary(items)}</Text>
      </View>
      <View accessibilityRole="list">
        {items.map((it) => {
          const c = checklistColor(colors, it.status);
          return (
            <View
              key={it.id}
              accessible
              accessibilityLabel={`${it.label}: ${tr(CHECKLIST_WORD[it.status])}${it.note ? `. ${it.note}` : ''}`}
              style={[styles.item, { borderTopColor: colors.borderSubtle, paddingVertical: spacing.sm }]}
            >
              <Icon name={{ glyph: CHECK_GLYPH[it.status] }} size={16} color={c} style={{ width: 20, marginRight: spacing.sm }} />
              <View style={styles.itemText}>
                <Text style={[textStyleFor(textStyles.bodySmall, it.label, '400'), { color: colors.textPrimary }]}>{it.label}</Text>
                {it.note ? <Text style={[textStyles.caption, { color: colors.textSecondary }]}>{it.note}</Text> : null}
              </View>
              <Text style={[textStyles.caption, { color: c, marginLeft: spacing.sm, fontFamily: textStyles.labelSmall.fontFamily }]}>
                {tr(CHECKLIST_WORD[it.status])}
              </Text>
            </View>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  steps: { flexDirection: 'row', alignItems: 'flex-start' },
  step: { flex: 1, alignItems: 'center', minHeight: 44 },
  marker: { width: 28, height: 28, borderRadius: 14, borderWidth: 2, alignItems: 'center', justifyContent: 'center' },
  stepLabel: { textAlign: 'center', marginTop: 4, paddingHorizontal: 2 },
  head: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 },
  item: { flexDirection: 'row', alignItems: 'flex-start', borderTopWidth: StyleSheet.hairlineWidth },
  itemText: { flex: 1 },
});
