import React from 'react';
import { Text, View } from 'react-native';
import { useTheme } from '../../theme';
import { Badge, Button, Card } from '../../components';
import { PlausibilityResponse } from '../../api';
import { humanizeEnum } from '../../services/labels';

/** The bounded clinical plausibility check (ADR-011): machine-derived, never a medical
 *  necessity determination; states what it could not assess. */
export const PlausibilityCard: React.FC<{
  plausibility: PlausibilityResponse | null;
  ready: boolean;
  onCheck: () => void;
}> = ({ plausibility, ready, onCheck }) => {
  const { colors, spacing, typography } = useTheme();
  return (
    <Card style={{ marginVertical: spacing.sm }}>
      <Button
        title="🩺 Check clinical plausibility"
        onPress={onCheck}
        variant="outline"
        size="sm"
        disabled={!ready}
      />
      {plausibility && (
        <View style={{ marginTop: spacing.sm, gap: spacing.xs }}>
          <View style={{ flexDirection: 'row', gap: spacing.xs, flexWrap: 'wrap' }}>
            <Badge label="Machine-derived" variant="info" />
            <Badge
              label={humanizeEnum(plausibility.assessment.status)}
              variant={plausibility.assessment.status === 'PLAUSIBLE' ? 'success' : 'warning'}
            />
          </View>
          <Text style={{ color: colors.textPrimary, fontSize: typography.sizes.sm }}>{plausibility.assessment.summary}</Text>
          {plausibility.assessment.not_assessed_items.length > 0 && (
            <Text style={{ color: colors.statusWarning, fontSize: typography.sizes.xs }}>
              Not assessed (outside the reference): {plausibility.assessment.not_assessed_items.join(', ')}
            </Text>
          )}
          <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>{plausibility.assessment.guideline_note}</Text>
          <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs, fontWeight: '700' }}>
            {plausibility.assessment.disclaimer}
          </Text>
        </View>
      )}
    </Card>
  );
};
