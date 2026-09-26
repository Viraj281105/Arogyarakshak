import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Switch, StyleSheet } from 'react-native';
import { useTheme } from '../theme';
import { Card } from './Card';
import { Button } from './Button';
import { Badge } from './Badge';
import { api } from '../api/endpoints';
import { ApiError, CaseClinicalReview, ClinicalStatement, ReviewerProfile } from '../api/types';

/**
 * ADR-011 patient-side clinical review. The patient chooses what is shared and with whom;
 * a named doctor writes and confirms their own statement. Verification wording is always
 * the server's `verification_label` — never upgraded here.
 *
 * Copy is English-first: Hindi/Marathi medico-legal wording is pending native-speaker review.
 */

const STATUS_TEXT: Record<CaseClinicalReview['status'], string> = {
  REQUESTED: 'Requested — choose a doctor',
  ASSIGNED: 'Waiting for the doctor to accept',
  IN_REVIEW: 'Doctor is reviewing',
  COMPLETED: 'Completed',
  DECLINED: 'Doctor declined — choose another',
  CANCELLED: 'Cancelled — access revoked',
};

export const StatementView: React.FC<{ statement: ClinicalStatement }> = ({ statement }) => {
  const { colors, spacing, typography } = useTheme();
  const rv = statement.reviewer_snapshot;
  const small = { color: colors.textSecondary, fontSize: typography.sizes.xs };
  return (
    <View style={[styles.statement, { borderColor: colors.statusSuccess, padding: spacing.sm, marginTop: spacing.sm }]}>
      <View style={{ flexDirection: 'row', gap: spacing.xs, flexWrap: 'wrap' }}>
        <Badge label="Human-authored" variant="success" />
        <Badge label={`v${statement.statement_version} · ${statement.status}`} variant="info" />
      </View>
      {rv && (
        <View style={{ marginTop: spacing.xs }}>
          <Text style={{ color: colors.textPrimary, fontWeight: '700' }}>
            {rv.name} · {rv.category_label}
            {rv.specialty ? ` · ${rv.specialty}` : ''}
          </Text>
          {rv.registration_number ? (
            <Text style={small}>
              Registration: {rv.registration_number}
              {rv.registration_authority ? ` (${rv.registration_authority})` : ''}
            </Text>
          ) : null}
          <Text style={{ color: colors.statusWarning, fontSize: typography.sizes.xs }}>{rv.verification_label}</Text>
        </View>
      )}
      <Text style={[small, { marginTop: spacing.xs }]}>
        Conflict of interest: {statement.coi_label}
        {statement.coi_disclosure ? ` — ${statement.coi_disclosure}` : ''}
      </Text>
      <Text style={[small, { marginTop: spacing.xs }]}>Reviewer&apos;s own statement (verbatim):</Text>
      <Text style={{ color: colors.textPrimary, fontSize: typography.sizes.sm }}>{statement.reviewer_statement}</Text>
      <Text style={[small, { marginTop: spacing.xs }]}>Limitations: {statement.limitations}</Text>
      <Text style={[small, { marginTop: spacing.xs }]}>
        This is the named reviewer&apos;s own professional opinion — not an insurer determination and not a finding of ArogyaRakshak.
      </Text>
    </View>
  );
};

export interface ClinicalReviewCardProps {
  caseId: string | null;
  sourceModule: 'billnyay' | 'bimanyay';
  recommendationReason?: string | null;
  trigger?: 'MANUAL' | 'PLAUSIBILITY_FLAG' | 'DENIAL_CATEGORY';
  insurerName?: string;
}

export const ClinicalReviewCard: React.FC<ClinicalReviewCardProps> = ({
  caseId,
  sourceModule,
  recommendationReason,
  trigger = 'MANUAL',
  insurerName,
}) => {
  const { colors, spacing, typography } = useTheme();
  const [reviews, setReviews] = useState<CaseClinicalReview[]>([]);
  const [doctors, setDoctors] = useState<ReviewerProfile[]>([]);
  const [shareConsent, setShareConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!caseId) return;
    try {
      const [list, directory] = await Promise.all([
        api.clinical.listReviews(caseId, sourceModule),
        api.clinical.doctorDirectory(),
      ]);
      setReviews(list.filter((r) => r.review_type === 'CLINICAL_STATEMENT'));
      setDoctors(directory);
      setError(null);
    } catch (err) {
      setError((err as ApiError).detail || (err as ApiError).message);
    }
  }, [caseId, sourceModule]);

  useEffect(() => {
    load();
  }, [load]);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await load();
    } catch (err) {
      setError((err as ApiError).detail || (err as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  if (!caseId) return null;

  return (
    <Card style={{ marginVertical: spacing.sm }}>
      <Text style={{ color: colors.textPrimary, fontWeight: '700', fontSize: typography.sizes.md }}>
        🩺 Clinical review by a named doctor
      </Text>
      <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.sm, marginVertical: spacing.xs }}>
        ArogyaRakshak will not invent a clinical opinion. You can share this case&apos;s de-identified evidence with a doctor
        you choose; they write and sign their own statement with their conflict of interest disclosed.
      </Text>
      {recommendationReason ? (
        <Text style={{ color: colors.statusWarning, fontSize: typography.sizes.xs }}>
          Machine-derived reason review is suggested: {recommendationReason}
        </Text>
      ) : null}
      {error && <Text style={{ color: '#ef4444', fontSize: 13 }}>⚠️ {error}</Text>}

      <View style={[styles.row, { marginVertical: spacing.sm }]}>
        <Switch
          value={shareConsent}
          onValueChange={setShareConsent}
          accessibilityLabel="Agree to share case evidence with the doctor I assign"
        />
        <Text style={{ color: colors.textPrimary, flex: 1, fontSize: typography.sizes.xs }}>
          I agree to share this case&apos;s de-identified evidence with the doctor I assign, for this review only.
        </Text>
      </View>
      <Button
        title="Request Clinical Review"
        onPress={() =>
          act(() =>
            api.clinical.requestReview(caseId, {
              source_module: sourceModule,
              trigger,
              insurer_name: insurerName || undefined,
              share_with_reviewer_consent: shareConsent,
            })
          )
        }
        disabled={busy || !shareConsent}
        size="sm"
      />
      {reviews.length > 0 && (
        <Button title="↻ Refresh status" onPress={() => act(async () => undefined)} variant="ghost" size="sm" />
      )}

      {reviews.map((review) => (
        <View key={review.review_id} style={[styles.item, { borderColor: colors.borderSubtle, paddingTop: spacing.sm, marginTop: spacing.sm }]}>
          <Badge label={STATUS_TEXT[review.status]} variant={review.status === 'COMPLETED' ? 'success' : 'info'} />
          {review.assigned_reviewer ? (
            <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs, marginTop: spacing.xs }}>
              {review.assigned_reviewer.name} · {review.assigned_reviewer.verification_label}
              {review.coi_label ? ` · COI: ${review.coi_label}` : ''}
            </Text>
          ) : null}
          {['REQUESTED', 'DECLINED', 'ASSIGNED'].includes(review.status) &&
            doctors.map((d) => (
              <Button
                key={d.id}
                title={`Assign ${d.name} (${d.verification_label})`}
                onPress={() => act(() => api.clinical.assignReviewer(caseId, review.review_id, d.id))}
                variant="outline"
                size="sm"
                disabled={busy}
              />
            ))}
          {review.current_statement ? (
            <StatementView statement={review.current_statement} />
          ) : review.status !== 'CANCELLED' ? (
            <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs, marginTop: spacing.xs }}>
              {review.draft_in_progress
                ? 'The doctor is drafting. Nothing is shown until they finalize and confirm it.'
                : 'No human clinical statement exists for this review yet.'}
            </Text>
          ) : null}
          {review.status !== 'CANCELLED' && (
            <Button
              title="Cancel & revoke access"
              onPress={() => act(() => api.clinical.cancelReview(caseId, review.review_id))}
              variant="danger"
              size="sm"
              disabled={busy}
            />
          )}
        </View>
      ))}
    </Card>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  item: { borderTopWidth: StyleSheet.hairlineWidth, gap: 6 },
  statement: { borderWidth: 1, borderRadius: 10 },
});
