import React from 'react';
import { StyleSheet, Text, View, ViewStyle } from 'react-native';
import { useTheme, textStyles, textStyleFor } from '../../theme';
import { Card } from '../Card';
import { Icon } from './Icon';
import { EVIDENCE_COPY, type EvidenceState } from './evidence';
import { confidenceBucket } from './logic';
import {
  confidenceColor,
  estimateSwatch,
  evidenceSwatch,
  statusBadgeSwatch,
  type StatusTone,
} from './tones';
import { tr, msg, useTranslation } from '../../translations/tr';

/**
 * The one evidence badge (eight states, same vocabulary and citation mapping as web). Always a
 * text label next to a distinct glyph, never colour alone; the meaning is the accessibility hint.
 */
export function EvidenceBadge({
  state,
  label,
  size = 'md',
  showMeaning = false,
  style,
}: {
  state: EvidenceState;
  /** Override the visible label (e.g. a translated string); defaults to the vocabulary label. */
  label?: string;
  size?: 'sm' | 'md';
  /** Render the meaning as visible text under the badge (for legends). */
  showMeaning?: boolean;
  style?: ViewStyle;
}) {
  useTranslation();
  const { colors, spacing, radii } = useTheme();
  const s = evidenceSwatch(colors, state);
  const copy = EVIDENCE_COPY[state];
  const text = label ?? tr(copy.label);
  const preset = size === 'sm' ? textStyles.caption : textStyles.labelSmall;
  return (
    <View style={[styles.wrap, style]}>
      <View
        accessible
        accessibilityRole="text"
        accessibilityLabel={tr('Evidence: {label}', { label: text })}
        accessibilityHint={tr(copy.meaning)}
        testID={`evidence-${state}`}
        style={[
          styles.badge,
          {
            backgroundColor: s.bg ?? undefined,
            borderColor: s.border ?? undefined,
            borderRadius: radii.full,
            paddingHorizontal: size === 'sm' ? spacing.sm - 2 : spacing.sm,
            paddingVertical: size === 'sm' ? 1 : 3,
          },
        ]}
      >
        <Icon name={{ evidence: state }} size={size === 'sm' ? 11 : 13} color={s.fg} />
        <Text style={[textStyleFor(preset, text, '600'), { color: s.fg, marginLeft: 4 }]}>{text}</Text>
      </View>
      {showMeaning ? (
        <Text style={[textStyles.caption, { color: colors.textSecondary, marginTop: 2 }]}>{tr(copy.meaning)}</Text>
      ) : null}
    </View>
  );
}

/** A general status chip (process state, not evidence). Text is required; the tone dot only reinforces it. */
export function StatusBadge({ tone, label, style }: { tone: StatusTone; label: string; style?: ViewStyle }) {
  const { colors, spacing, radii } = useTheme();
  const s = statusBadgeSwatch(colors, tone);
  return (
    <View
      accessible
      accessibilityRole="text"
      accessibilityLabel={label}
      style={[
        styles.badge,
        {
          backgroundColor: s.bg ?? undefined,
          borderColor: s.border ?? undefined,
          borderRadius: radii.full,
          paddingHorizontal: spacing.sm,
          paddingVertical: 3,
        },
        style,
      ]}
    >
      <View style={[styles.dot, { backgroundColor: s.dot }]} />
      <Text style={[textStyleFor(textStyles.caption, label, '600'), { color: s.fg, marginLeft: 6 }]}>{label}</Text>
    </View>
  );
}

/**
 * Model or extraction confidence: a bar with its number and a word. It describes how sure the
 * extractor was, not whether the value is correct; `source` says who produced the number.
 */
export function ConfidenceIndicator({
  value,
  label = msg('Confidence'),
  source,
  style,
}: {
  /** 0..1, as returned by the API. */
  value: number;
  label?: string;
  /** Who computed it, e.g. "OCR engine". Required so a bare number never floats free. */
  source: string;
  style?: ViewStyle;
}) {
  useTranslation();
  const { colors, radii } = useTheme();
  const { pct, word } = confidenceBucket(value);
  const name = tr(label);
  const shownWord = tr(word);
  return (
    <View
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel={tr('{label}: {percent}%, {word}, from {source}', { label: name, percent: pct, word: shownWord, source })}
      accessibilityValue={{ min: 0, max: 100, now: pct, text: `${pct}% ${shownWord}` }}
      style={style}
    >
      <View style={styles.row}>
        <Text style={[textStyleFor(textStyles.labelSmall, name, '600'), { color: colors.textSecondary, flexShrink: 1 }]}>
          {name}
        </Text>
        <Text style={[textStyles.mono, { color: colors.textPrimary, marginLeft: 8 }]}>
          {pct}% · {shownWord}
        </Text>
      </View>
      <View style={[styles.track, { backgroundColor: colors.bgSurfaceSecondary, borderRadius: radii.full }]}>
        <View
          style={[
            styles.fill,
            { width: `${pct}%`, backgroundColor: confidenceColor(colors, word), borderRadius: radii.full },
          ]}
        />
      </View>
      <Text style={[textStyles.caption, { color: colors.textSecondary }]}>{tr('Source: {source}', { source })}</Text>
    </View>
  );
}

/**
 * A single headline figure. `basis` is mandatory: a figure is either an estimate or verified
 * against a source, and the card says which in words. `source` (and `period`) keep it honest.
 */
export function MetricCard({
  label,
  value,
  unit,
  basis,
  source,
  period,
  note,
  style,
}: {
  label: string;
  /** Pre-formatted value (use Intl.NumberFormat('en-IN') upstream). */
  value: string;
  unit?: string;
  basis: 'estimate' | 'verified';
  source: string;
  period?: string;
  note?: string;
  style?: ViewStyle;
}) {
  useTranslation();
  const { colors, spacing, radii } = useTheme();
  const est = estimateSwatch(colors);
  const basisWord = basis === 'verified' ? tr('Verified') : tr('Estimate');
  return (
    <Card
      reveal={false}
      style={style}
      accessible
      accessibilityLabel={tr('{label}: {value}. {basis}. Source: {source}.', {
        label,
        value: unit ? `${value} ${unit}` : value,
        basis: basisWord,
        source: period ? `${source}, ${period}` : source,
      })}
    >
      <View style={styles.row}>
        <Text style={[textStyleFor(textStyles.labelSmall, label, '600'), { color: colors.textSecondary, flexShrink: 1 }]}>
          {label}
        </Text>
        {basis === 'verified' ? (
          <EvidenceBadge state="verified" size="sm" style={{ marginLeft: spacing.sm }} />
        ) : (
          <View
            style={[
              styles.badge,
              {
                marginLeft: spacing.sm,
                backgroundColor: est.bg ?? undefined,
                borderColor: est.border ?? undefined,
                borderRadius: radii.full,
                paddingHorizontal: spacing.sm - 2,
                paddingVertical: 1,
              },
            ]}
          >
            <Text style={[textStyles.caption, { color: est.fg }]}>{tr('Estimate')}</Text>
          </View>
        )}
      </View>
      <Text style={[styles.value, { color: colors.textPrimary, marginTop: spacing.xs }]}>
        {value}
        {unit ? <Text style={[textStyles.bodySmall, { color: colors.textSecondary }]}> {unit}</Text> : null}
      </Text>
      <Text style={[textStyles.caption, { color: colors.textMuted, marginTop: spacing.xs }]}>
        {tr('Source: {source}', { source })}
        {period ? ` · ${period}` : ''}
      </Text>
      {note ? (
        <Text style={[textStyles.bodySmall, { color: colors.textSecondary, marginTop: spacing.xs }]}>{note}</Text>
      ) : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  wrap: { alignSelf: 'flex-start' },
  badge: { flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', borderWidth: 1 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  track: { height: 8, marginVertical: 6, overflow: 'hidden' },
  fill: { height: 8 },
  value: { ...textStyles.mono, fontSize: 24, lineHeight: 32 },
});
