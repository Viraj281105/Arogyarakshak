import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { Card } from './Card';
import { Button } from './Button';
import { api } from '../api/endpoints';
import { ApiError, ResolutionDecision } from '../api/types';
import { formatMatchScore } from '../services/resolution';

export interface ResolutionReviewCardProps {
  caseId: string | null;
  /** Change this (e.g. when a scan completes) to reload pending questions. */
  refreshToken?: unknown;
}

/**
 * "Are these the same?" prompts for Kadi's ASK decisions (#31). Nothing is merged until the
 * patient answers; each answer also feeds threshold calibration (#88).
 */
export const ResolutionReviewCard: React.FC<ResolutionReviewCardProps> = ({ caseId, refreshToken }) => {
  const { colors, spacing, typography } = useTheme();
  const { t } = useLanguage();
  const r = t.resolution;
  const [decisions, setDecisions] = useState<ResolutionDecision[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadPending = useCallback(async () => {
    if (!caseId) return;
    try {
      setDecisions(await api.kadi.getPendingResolutions(caseId));
      setError(null);
    } catch (err) {
      setError((err as ApiError).message || 'Could not load review items.');
    }
  }, [caseId]);

  useEffect(() => {
    loadPending();
  }, [loadPending, refreshToken]);

  const answer = async (decision: ResolutionDecision, sameEntity: boolean) => {
    if (!caseId) return;
    setBusyId(decision.id);
    try {
      await api.kadi.submitResolutionFeedback(caseId, decision.id, sameEntity);
      setDecisions((prev) => prev.filter((d) => d.id !== decision.id));
    } catch (err) {
      const apiErr = err as ApiError;
      if (apiErr.statusCode === 409) {
        // Already answered, or the entities changed: no longer a pending question.
        setDecisions((prev) => prev.filter((d) => d.id !== decision.id));
      } else {
        setError(apiErr.message || 'Could not save your answer.');
      }
    } finally {
      setBusyId(null);
    }
  };

  if (!caseId || (decisions.length === 0 && !error)) return null;

  return (
    <Card style={{ marginVertical: spacing.sm }}>
      <Text style={{ color: colors.textPrimary, fontWeight: '700', fontSize: typography.sizes.md }}>{r.title}</Text>
      <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.sm, marginVertical: spacing.xs }}>
        {r.intro}
      </Text>
      {error && <Text style={{ color: '#ef4444', fontSize: 13 }}>⚠️ {error}</Text>}

      {decisions.map((decision) => (
        <View
          key={decision.id}
          style={[styles.item, { borderColor: colors.borderSubtle, paddingVertical: spacing.sm }]}
        >
          <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>{r.mentionLabel}</Text>
          <Text style={{ color: colors.textPrimary, fontWeight: '600' }}>{decision.mention_name}</Text>
          <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs, marginTop: spacing.xs }}>
            {r.existingLabel}
          </Text>
          <Text style={{ color: colors.textPrimary, fontWeight: '600' }}>{decision.candidate_name}</Text>
          <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs, marginVertical: spacing.xs }}>
            {r.confidenceLabel}: {formatMatchScore(decision.confidence) ?? r.unavailable} · {r.uncalibratedNote}
          </Text>
          <View style={{ gap: spacing.xs }}>
            <Button
              title={r.confirmBtn}
              onPress={() => answer(decision, true)}
              variant="primary"
              size="sm"
              disabled={busyId === decision.id}
            />
            <Button
              title={r.rejectBtn}
              onPress={() => answer(decision, false)}
              variant="outline"
              size="sm"
              disabled={busyId === decision.id}
            />
          </View>
        </View>
      ))}
    </Card>
  );
};

const styles = StyleSheet.create({
  item: { borderTopWidth: StyleSheet.hairlineWidth },
});
