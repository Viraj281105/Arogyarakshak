import React from 'react';
import { View, Text } from 'react-native';
import { useTheme } from '../theme';
import { Card } from './Card';
import { Button } from './Button';
import { AgentStreamVisualizer } from './AgentStreamVisualizer';
import { CaseProcessing } from '../hooks/useCaseProcessing';

/**
 * The one place a module screen shows where its case is in processing: live progress,
 * an honest failure, or — for a stream that went quiet — "Processing is taking longer
 * than expected" with a way to refresh the status. It never shows completion that the
 * server did not report.
 */
export const ProcessingStatusCard: React.FC<{ proc: CaseProcessing }> = ({ proc }) => {
  const { colors, spacing, typography } = useTheme();
  if (!proc.caseId || proc.phase === 'idle') return null;

  if (proc.timedOut) {
    return (
      <Card style={{ marginVertical: spacing.sm, borderColor: colors.statusWarning, borderWidth: 1 }}>
        <Text style={{ color: colors.statusWarning, fontWeight: '700', fontSize: typography.sizes.sm }}>
          ⏳ Processing is taking longer than expected.
        </Text>
        <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs, marginVertical: spacing.xs }}>
          Your document may still be being read. Nothing below has been checked yet — refresh the status before relying on
          any result.
        </Text>
        <Button title="Refresh status" onPress={proc.refreshStatus} variant="outline" size="sm" />
      </Card>
    );
  }

  if (proc.failed) {
    return (
      <Card style={{ marginVertical: spacing.sm, borderColor: colors.statusDanger, borderWidth: 1 }}>
        <Text style={{ color: colors.statusDanger, fontWeight: '700', fontSize: typography.sizes.sm }}>
          ⚠️ This document could not be processed.
        </Text>
        {proc.message ? (
          <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs, marginVertical: spacing.xs }}>
            {proc.message}
          </Text>
        ) : null}
        <View style={{ gap: spacing.xs }}>
          <Button title="Refresh status" onPress={proc.refreshStatus} variant="outline" size="sm" />
        </View>
      </Card>
    );
  }

  if (proc.processing) {
    return (
      <AgentStreamVisualizer
        progress={proc.progress}
        latestEvent={proc.sse.latestEvent}
        isStreaming
        isCompleted={false}
        error={null}
      />
    );
  }

  // Ready: a quiet confirmation (only when this screen actually watched it finish).
  if (proc.sse.events.some((e) => e.status === 'completed')) {
    return (
      <AgentStreamVisualizer progress={100} latestEvent={proc.sse.latestEvent} isStreaming={false} isCompleted error={null} />
    );
  }
  return null;
};
