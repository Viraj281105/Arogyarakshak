import React from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { useTheme } from '../theme';
import { SSEStreamEvent } from '../hooks/useSSEStream';
import { Badge } from './Badge';

interface AgentStreamVisualizerProps {
  progress: number;
  latestEvent: SSEStreamEvent | null;
  isStreaming: boolean;
  isCompleted: boolean;
  error?: string | null;
}

export const AgentStreamVisualizer: React.FC<AgentStreamVisualizerProps> = ({
  progress,
  latestEvent,
  isStreaming,
  isCompleted,
  error,
}) => {
  const { colors, spacing, typography, radii } = useTheme();

  const getStepIndex = (status?: string): number => {
    switch (status) {
      case 'upload_received':
        return 1;
      case 'ocr_start':
        return 2;
      case 'extraction_start':
      case 'database_write':
        return 3;
      case 'completed':
        return 4;
      default:
        return 1;
    }
  };

  const currentStep = getStepIndex(latestEvent?.status);

  return (
    <View style={[styles.container, { backgroundColor: colors.bgSurface, borderColor: colors.borderSubtle, borderRadius: radii.md, padding: spacing.md }]}>
      <View style={styles.headerRow}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          {isStreaming && <ActivityIndicator size="small" color={colors.brandCyan} />}
          <Text style={{ color: colors.textPrimary, fontWeight: '700', fontSize: typography.sizes.sm }}>
            {isCompleted ? '✓ Case Ingestion Completed' : '⚡ Kadi Real-Time Stream'}
          </Text>
        </View>
        <Badge
          label={isCompleted ? 'Ready' : `${progress}%`}
          variant={isCompleted ? 'success' : error ? 'danger' : 'brand'}
        />
      </View>

      {/* Progress Bar */}
      <View style={[styles.progressBarTrack, { backgroundColor: 'rgba(255,255,255,0.08)' }]}>
        <View
          style={[
            styles.progressBarFill,
            {
              width: `${Math.min(Math.max(progress, isCompleted ? 100 : 8), 100)}%`,
              backgroundColor: isCompleted ? '#22c55e' : colors.brandCyan,
            },
          ]}
        />
      </View>

      {/* Pipeline Step Indicators */}
      <View style={styles.stepsRow}>
        {[
          { step: 1, label: 'Upload' },
          { step: 2, label: 'OCR' },
          { step: 3, label: 'Entities' },
          { step: 4, label: 'Complete' },
        ].map(({ step, label }) => {
          const isActive = currentStep === step && isStreaming;
          const isDone = currentStep > step || isCompleted;

          return (
            <View key={step} style={styles.stepItem}>
              <View
                style={[
                  styles.stepDot,
                  {
                    backgroundColor: isDone
                      ? '#22c55e'
                      : isActive
                      ? colors.brandCyan
                      : 'rgba(255,255,255,0.1)',
                  },
                ]}
              />
              <Text
                style={{
                  fontSize: 10,
                  marginTop: 3,
                  color: isDone ? '#22c55e' : isActive ? colors.textPrimary : colors.textMuted,
                  fontWeight: isActive ? '700' : '400',
                }}
              >
                {label}
              </Text>
            </View>
          );
        })}
      </View>

      {/* Live Log Message */}
      {latestEvent?.log && (
        <Text style={[styles.logText, { color: colors.textSecondary, fontSize: typography.sizes.xs }]}>
          💬 {latestEvent.log}
        </Text>
      )}

      {/* Error message */}
      {error && (
        <Text style={[styles.errorText, { color: colors.statusDanger, fontSize: typography.sizes.xs }]}>
          ⚠️ {error}
        </Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    borderWidth: 1,
    marginVertical: 8,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  progressBarTrack: {
    height: 4,
    borderRadius: 2,
    overflow: 'hidden',
    marginBottom: 10,
  },
  progressBarFill: {
    height: '100%',
  },
  stepsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  stepItem: {
    alignItems: 'center',
    flex: 1,
  },
  stepDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  logText: {
    fontStyle: 'italic',
    marginTop: 4,
  },
  errorText: {
    marginTop: 4,
    fontWeight: '600',
  },
});
