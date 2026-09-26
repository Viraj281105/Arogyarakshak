import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Switch, StyleSheet } from 'react-native';
import { useTheme } from '../theme';
import { Card } from './Card';
import { Button } from './Button';
import { Badge } from './Badge';
import { api } from '../api/endpoints';
import { ApiError, ReadinessResponse, ReviewerProfile, SafetyEvaluation, TranscriptionTask } from '../api/types';

/**
 * ADR-011 mobile surfaces: safety escalations, preauth readiness, and uncertain OCR
 * transcription. English-first copy; Hindi/Marathi pending native-speaker review.
 */

export const SafetyNotice: React.FC<{ caseId: string | null; refreshToken?: unknown }> = ({ caseId, refreshToken }) => {
  const { colors, spacing, typography } = useTheme();
  const [evaluation, setEvaluation] = useState<SafetyEvaluation | null>(null);

  useEffect(() => {
    if (!caseId) return;
    api.clinical.safety(caseId).then(setEvaluation).catch(() => setEvaluation(null));
  }, [caseId, refreshToken]);

  if (!caseId || !evaluation) return null;
  if (evaluation.escalations.length === 0) {
    return (
      <Text style={{ color: colors.textMuted, fontSize: typography.sizes.xs, marginVertical: spacing.xs }}>
        🛡️ {evaluation.coverage_note} {evaluation.disclaimer}
      </Text>
    );
  }
  return (
    <Card style={{ marginVertical: spacing.sm, borderColor: colors.statusDanger, borderWidth: 2 }}>
      <Text style={{ color: colors.statusDanger, fontWeight: '700', fontSize: typography.sizes.md }}>⚠️ Clinical safety check</Text>
      {evaluation.escalations.map((esc) => (
        <View key={esc.rule_id} style={{ marginTop: spacing.sm }}>
          <Text style={{ color: colors.textPrimary, fontWeight: '700' }}>
            {esc.severity === 'URGENT' ? 'Urgent: ' : ''}
            {esc.title}
          </Text>
          <Text style={{ color: colors.textPrimary }}>{esc.message}</Text>
          <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>
            Matched: {esc.matched_terms.join(', ')} · Rule v{esc.rule_version} · Source: {esc.source.name}
          </Text>
        </View>
      ))}
      <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs, marginTop: spacing.sm }}>{evaluation.disclaimer}</Text>
    </Card>
  );
};

const READINESS_MARK: Record<string, string> = {
  PRESENT: '✓',
  MISSING: '✗',
  NEEDS_CLINICAL_CONFIRMATION: '?',
  CONFIRMED_BY_REVIEWER: '✓',
  REJECTED_BY_REVIEWER: '✗',
  REVIEWER_COULD_NOT_DETERMINE: '?',
};

export const ReadinessCard: React.FC<{ caseId: string | null }> = ({ caseId }) => {
  const { colors, spacing, typography } = useTheme();
  const [report, setReport] = useState<ReadinessResponse | null>(null);
  const [shareConsent, setShareConsent] = useState(false);
  const [requested, setRequested] = useState<string | null>(null);
  const [doctors, setDoctors] = useState<ReviewerProfile[]>([]);
  const [error, setError] = useState<string | null>(null);

  if (!caseId) return null;

  const check = async () => {
    setError(null);
    try {
      setReport(await api.daavisetu.readiness(caseId));
    } catch (err) {
      setError((err as ApiError).detail || (err as ApiError).message);
    }
  };

  const pendingFacts = report?.items.filter((i) => i.status === 'NEEDS_CLINICAL_CONFIRMATION') ?? [];

  const requestConfirmation = async () => {
    setError(null);
    try {
      const review = await api.daavisetu.requestClinicalConfirmation(caseId, pendingFacts.map((f) => f.item_id), shareConsent);
      setRequested(review.review_id);
      setDoctors(await api.clinical.doctorDirectory());
    } catch (err) {
      setError((err as ApiError).detail || (err as ApiError).message);
    }
  };

  return (
    <Card style={{ marginVertical: spacing.sm }}>
      <Text style={{ color: colors.textPrimary, fontWeight: '700', fontSize: typography.sizes.md }}>📑 Pre-authorization readiness</Text>
      <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs, marginVertical: spacing.xs }}>
        Checks which commonly requested documents are in your case. It does not predict approval.
      </Text>
      <Button title="Check documentation readiness" onPress={check} size="sm" />
      {error && <Text style={{ color: '#ef4444', fontSize: 13 }}>⚠️ {error}</Text>}
      {report && (
        <View style={{ marginTop: spacing.sm }}>
          <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>Guidance: {report.guidance_label}</Text>
          {report.items.map((item) => (
            <Text key={item.item_id} style={{ color: colors.textPrimary, fontSize: typography.sizes.sm, marginTop: 2 }}>
              {READINESS_MARK[item.status]} {item.label} — {item.status.replaceAll('_', ' ').toLowerCase()}
              {item.evidence_strength === 'KEYWORD_MATCH' ? ' (keyword match — weak evidence)' : ''}
            </Text>
          ))}
          {report.recommended_actions.map((a) => (
            <Text key={a} style={{ color: colors.statusWarning, fontSize: typography.sizes.xs, marginTop: spacing.xs }}>
              {a}
            </Text>
          ))}
          <Text style={{ color: colors.textMuted, fontSize: typography.sizes.xs, marginTop: spacing.xs }}>{report.disclaimer}</Text>
          {pendingFacts.length > 0 && !requested && (
            <>
              <View style={[styles.row, { marginTop: spacing.sm }]}>
                <Switch value={shareConsent} onValueChange={setShareConsent} accessibilityLabel="Agree to share evidence with a doctor" />
                <Text style={{ color: colors.textPrimary, flex: 1, fontSize: typography.sizes.xs }}>
                  I agree to share de-identified case evidence with the doctor I assign to confirm these facts.
                </Text>
              </View>
              <Button title={`Ask a doctor to confirm ${pendingFacts.length} fact(s)`} onPress={requestConfirmation} disabled={!shareConsent} size="sm" variant="secondary" />
            </>
          )}
          {requested &&
            doctors.map((d) => (
              <Button
                key={d.id}
                title={`Assign ${d.name} (${d.verification_label})`}
                onPress={() =>
                  api.clinical
                    .assignReviewer(caseId, requested, d.id)
                    .then(() => setDoctors([]))
                    .catch((err: ApiError) => setError(err.detail || err.message))
                }
                variant="outline"
                size="sm"
              />
            ))}
        </View>
      )}
    </Card>
  );
};

const TASK_STATUS: Record<TranscriptionTask['status'], string> = {
  OPEN: 'Awaiting a human reading',
  AWAITING_SECOND_REVIEW: 'Needs a second independent reading',
  RESOLVED: 'Resolved by independent human readings',
  HUMAN_ESCALATION_REQUIRED: 'Readers disagreed — confirm with the prescriber or pharmacist',
  CANCELLED: 'Cancelled',
};

export const TranscriptionCard: React.FC<{ caseId: string | null; medicines: { id: string; name: string }[] }> = ({ caseId, medicines }) => {
  const { colors, spacing, typography } = useTheme();
  const [tasks, setTasks] = useState<TranscriptionTask[]>([]);
  const [readers, setReaders] = useState<ReviewerProfile[]>([]);
  const [shareConsent, setShareConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!caseId) return;
    try {
      const [list, directory] = await Promise.all([api.clinical.transcriptions(caseId), api.clinical.readerDirectory()]);
      setTasks(list);
      setReaders(directory);
    } catch (err) {
      setError((err as ApiError).detail || (err as ApiError).message);
    }
  }, [caseId]);

  useEffect(() => {
    load();
  }, [load]);

  if (!caseId) return null;

  const act = (fn: () => Promise<unknown>) =>
    fn()
      .then(load)
      .catch((err: ApiError) => setError(err.detail || err.message));

  const flagged = new Set(tasks.filter((t) => t.status !== 'CANCELLED').map((t) => t.entity_id));

  return (
    <Card style={{ marginVertical: spacing.sm }}>
      <Text style={{ color: colors.textPrimary, fontWeight: '700', fontSize: typography.sizes.md }}>✍️ Unclear prescription text</Text>
      <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs, marginVertical: spacing.xs }}>
        When the software is unsure what a prescription says, trained human readers (pharmacists, transcriptionists) read
        it instead of the app guessing. Medicine fields need two readings that agree. The image is never stored.
      </Text>
      {error && <Text style={{ color: '#ef4444', fontSize: 13 }}>⚠️ {error}</Text>}
      {medicines.map((m) => (
        <Button
          key={m.id}
          title={flagged.has(m.id) ? `✓ ${m.name} flagged` : `Flag “${m.name}” as possibly misread`}
          onPress={() => act(() => api.clinical.flagForTranscription(caseId, m.id))}
          disabled={flagged.has(m.id)}
          variant="outline"
          size="sm"
        />
      ))}
      {tasks.length > 0 && (
        <View style={[styles.row, { marginTop: spacing.sm }]}>
          <Switch value={shareConsent} onValueChange={setShareConsent} accessibilityLabel="Agree to share masked text with readers" />
          <Text style={{ color: colors.textPrimary, flex: 1, fontSize: typography.sizes.xs }}>
            I agree to share the masked, redacted text with the readers I assign.
          </Text>
        </View>
      )}
      {tasks.map((task) => (
        <View key={task.task_id} style={[styles.item, { borderColor: colors.borderSubtle, paddingTop: spacing.sm, marginTop: spacing.sm }]}>
          <Badge label={`${task.field_type.replace('_', ' ')} · ${task.risk_level} risk`} variant={task.risk_level === 'HIGH' ? 'danger' : 'info'} />
          <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>
            {TASK_STATUS[task.status]} · readings {task.readings_received}/{task.required_reviews}
          </Text>
          <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>Context: {task.masked_context}</Text>
          {task.final_value ? (
            <Text style={{ color: colors.textPrimary }}>
              Human-confirmed reading: {task.final_value} ({task.final_value_provenance})
            </Text>
          ) : null}
          {(task.status === 'OPEN' || task.status === 'AWAITING_SECOND_REVIEW') &&
            readers.map((r) => (
              <Button
                key={r.id}
                title={`Assign ${r.name} — ${r.category_label} (${r.verification_label})`}
                onPress={() => act(() => api.clinical.assignTranscription(caseId, task.task_id, r.id, shareConsent))}
                disabled={!shareConsent}
                variant="ghost"
                size="sm"
              />
            ))}
        </View>
      ))}
    </Card>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  item: { borderTopWidth: StyleSheet.hairlineWidth, gap: 4 },
});
