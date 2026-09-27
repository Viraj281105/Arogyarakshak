import React, { useState } from 'react';

// Statutory SLA tier states (bimanyay.tracker) in plain language.
const SLA_STATUS_LABEL: Record<string, string> = {
  ACTIVE: 'Current step',
  OVERDUE: 'Deadline passed',
  COMPLETED: 'Done',
  PENDING: 'Later step',
};
import { View, Text, StyleSheet, ScrollView, TextInput, Alert, Share } from 'react-native';
import { useRoute, RouteProp } from '@react-navigation/native';
import { BottomTabParamList } from '../navigation/types';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { Card, Button, Badge, ClinicalReviewCard, ProcessingStatusCard } from '../components';
import { api, BimaNyayAnalysisResponse, BimaNyayTimelineResponse, ApiError } from '../api';
import { getCaseAccessToken } from '../api/caseAuth';
import { useOfflineQueue } from '../hooks/useOfflineQueue';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { useCaseProcessing } from '../hooks/useCaseProcessing';
import { useActiveCaseId } from '../hooks/useActiveCase';
import { resolveCaseId } from '../services/activeCase';

export const BimaNyayScreen: React.FC = () => {
  const route = useRoute<RouteProp<BottomTabParamList, 'BimaNyay'>>();
  const { colors, spacing, typography } = useTheme();
  const { t, language } = useLanguage();
  const { enqueueAction } = useOfflineQueue();
  const { isOnline } = useNetworkStatus();
  const m = t.modules.bimanyay;
  // ADR-011: a scanned denial letter arrives with its case; analyses are then linked to it.
  const activeCaseId = useActiveCaseId();
  const caseId = resolveCaseId(route.params?.caseId, activeCaseId);
  const proc = useCaseProcessing(caseId);
  const processing = !proc.ready;

  // Form state
  // Empty by default: pre-filled values were submitted verbatim by users who did not
  // edit them, producing determinations about a fabricated person.
  const [policyNumber, setPolicyNumber] = useState('');
  const [insurerName, setInsurerName] = useState('');
  const [policyAge, setPolicyAge] = useState('');
  const [claimedAmount, setClaimedAmount] = useState('');
  const [deniedAmount, setDeniedAmount] = useState('');
  const [denialCategory, setDenialCategory] = useState('PED_NON_DISCLOSURE');
  const [denialReason, setDenialReason] = useState('');
  const [diagnosis, setDiagnosis] = useState('');

  // Result state
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BimaNyayAnalysisResponse | null>(null);
  const [timeline, setTimeline] = useState<BimaNyayTimelineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [offlineQueued, setOfflineQueued] = useState(false);
  const [activeTab, setActiveTab] = useState<'gro' | 'bimabharosa' | 'ombudsman'>('gro');

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    setOfflineQueued(false);

    const analysisPayload = {
      policy_number: policyNumber,
      insurer_name: insurerName,
      policy_age_years: parseFloat(policyAge) || 0,
      claimed_amount: parseFloat(claimedAmount) || 0,
      denied_or_deducted_amount: parseFloat(deniedAmount) || 0,
      denial_category: denialCategory,
      denial_reason_raw: denialReason,
      diagnosis,
    };

    try {
      const analysisResult = await api.bimanyay.analyze(
        analysisPayload,
        language,
        caseId ?? undefined,
        caseId ? getCaseAccessToken(caseId) : undefined
      );
      setResult(analysisResult);

      // Also fetch statutory timeline
      const today = new Date().toISOString().split('T')[0];
      const timelineResult = await api.bimanyay.getTimeline({
        insurer_name: insurerName,
        date_initiated: today,
        claim_number: policyNumber,
        current_tier: 'LEVEL_1_GRO',
      });
      setTimeline(timelineResult);
    } catch (err) {
      const apiErr = err as ApiError;
      const queuedId = await enqueueAction('ANALYZE_DENIAL', {
        data: analysisPayload,
        language,
      });
      if (queuedId) {
        setOfflineQueued(true);
        setError(
          !isOnline
            ? 'Device is offline. Denial audit queued; will sync automatically when reconnected.'
            : `${apiErr.message || 'Failed to analyze denial.'} (Queued for offline retry)`
        );
      } else {
        setOfflineQueued(false);
        setError('Could not save this for offline retry — please try again when back online.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!result) return;
    let text = result.level_1_gro_appeal;
    if (activeTab === 'bimabharosa') text = result.level_2_bimabharosa_text;
    if (activeTab === 'ombudsman') text = result.level_3_ombudsman_grounds;
    try {
      await Share.share({ message: text });
    } catch {
      Alert.alert('Appeal Draft', text);
    }
  };

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.bgBase }]}
      contentContainerStyle={[styles.content, { padding: spacing.md }]}
    >
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.textPrimary, fontSize: typography.sizes.xl }]}>
          🛡️ {m.title}
        </Text>
        <Badge label={m.statutory} variant="danger" />
      </View>

      <Text style={[styles.desc, { color: colors.textSecondary, fontSize: typography.sizes.sm, marginBottom: spacing.md }]}>
        {m.desc}
      </Text>

      <ProcessingStatusCard proc={proc} />

      {/* Input Form */}
      <Card style={{ marginBottom: spacing.md }}>
        <Text style={[styles.cardTitle, { color: colors.textPrimary, marginBottom: spacing.sm }]}>
          {m.cardTitle}
        </Text>

        <TextInput
          style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
          placeholder={m.policyNumber}
          placeholderTextColor={colors.textMuted}
          value={policyNumber}
          onChangeText={setPolicyNumber}
        />
        <TextInput
          style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
          placeholder={m.insurerName}
          placeholderTextColor={colors.textMuted}
          value={insurerName}
          onChangeText={setInsurerName}
        />
        <View style={styles.row}>
          <TextInput
            style={[styles.input, styles.halfInput, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
            placeholder={m.policyAge}
            keyboardType="numeric"
            placeholderTextColor={colors.textMuted}
            value={policyAge}
            onChangeText={setPolicyAge}
          />
          <TextInput
            style={[styles.input, styles.halfInput, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
            placeholder={m.claimedAmount}
            keyboardType="numeric"
            placeholderTextColor={colors.textMuted}
            value={claimedAmount}
            onChangeText={setClaimedAmount}
          />
        </View>
        <TextInput
          style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
          placeholder={m.deniedAmount}
          keyboardType="numeric"
          placeholderTextColor={colors.textMuted}
          value={deniedAmount}
          onChangeText={setDeniedAmount}
        />
        <Text style={[styles.cardTitle, { color: colors.textSecondary, fontSize: typography.sizes.sm, marginBottom: spacing.xs }]}>
          {m.denialCategoryLabel}
        </Text>
        <View style={[styles.row, { flexWrap: 'wrap', marginBottom: spacing.sm }]}>
          {(
            [
              ['PED_NON_DISCLOSURE', m.denialCategoryPedNonDisclosure],
              ['ROOM_RENT_CAPPING', m.denialCategoryRoomRentCapping],
              ['INVESTIGATION_ONLY', m.denialCategoryInvestigationOnly],
              ['DELAYED_INTIMATION', m.denialCategoryDelayedIntimation],
            ] as const
          ).map(([value, label]) => (
            <Button
              key={value}
              title={label}
              onPress={() => setDenialCategory(value)}
              variant={denialCategory === value ? 'primary' : 'secondary'}
              size="sm"
              style={{ marginRight: spacing.xs, marginBottom: spacing.xs }}
            />
          ))}
        </View>
        <TextInput
          style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
          placeholder={m.denialReason}
          placeholderTextColor={colors.textMuted}
          value={denialReason}
          onChangeText={setDenialReason}
          multiline
        />
        <TextInput
          style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
          placeholder={m.diagnosis}
          placeholderTextColor={colors.textMuted}
          value={diagnosis}
          onChangeText={setDiagnosis}
        />

        {error && <Text style={{ color: '#ef4444', fontSize: 13, marginBottom: 8 }}>⚠️ {error}</Text>}

        <Button
          title={loading ? m.auditing : m.auditBtn}
          onPress={handleAnalyze}
          variant="primary"
          disabled={loading}
        />
      </Card>

      {/* Results */}
      {result && (
        <Card style={{ marginBottom: spacing.md }}>
          <View style={[styles.row, { marginBottom: spacing.sm }]}>
            <Text style={{ color: colors.textPrimary, fontWeight: '700', fontSize: typography.sizes.md }}>
              {m.reversalScore} {(result.reversal_probability_score * 100).toFixed(0)}%
            </Text>
            {result.is_wrongful_denial && <Badge label={m.wrongful} variant="success" />}
          </View>
          <Text style={{ color: colors.textSecondary, fontSize: 12, marginBottom: spacing.sm }}>
            {m.heuristicDisclosure}
          </Text>

          {result.regulatory_violations.length > 0 && (
            <View style={{ marginBottom: spacing.sm }}>
              {result.regulatory_violations.map((v, idx) => (
                <Text key={idx} style={{ color: colors.textSecondary, fontSize: 12, marginBottom: 4 }}>
                  • {v.statute_or_circular}: {v.violation_summary}
                </Text>
              ))}
            </View>
          )}

          {/* Appeal Tabs */}
          <View style={[styles.row, { marginBottom: spacing.sm }]}>
            <Button
              title={m.groTab}
              onPress={() => setActiveTab('gro')}
              variant={activeTab === 'gro' ? 'primary' : 'secondary'}
              size="sm"
              style={{ flex: 1 }}
            />
            <Button
              title={m.bharosaTab}
              onPress={() => setActiveTab('bimabharosa')}
              variant={activeTab === 'bimabharosa' ? 'primary' : 'secondary'}
              size="sm"
              style={{ flex: 1, marginHorizontal: 4 }}
            />
            <Button
              title={m.ombudsmanTab}
              onPress={() => setActiveTab('ombudsman')}
              variant={activeTab === 'ombudsman' ? 'primary' : 'secondary'}
              size="sm"
              style={{ flex: 1 }}
            />
          </View>

          <Text style={{ color: colors.textPrimary, fontSize: 13, lineHeight: 20, marginBottom: spacing.sm }}>
            {activeTab === 'gro' && result.level_1_gro_appeal}
            {activeTab === 'bimabharosa' && result.level_2_bimabharosa_text}
            {activeTab === 'ombudsman' && result.level_3_ombudsman_grounds}
          </Text>

          <Button title={m.copyDraft} onPress={handleCopy} variant="secondary" size="sm" />
        </Card>
      )}

      {/* Timeline */}
      {timeline && timeline.timeline_events.length > 0 && (
        <Card>
          <Text style={[styles.cardTitle, { color: colors.textPrimary, marginBottom: spacing.sm }]}>
            {m.timelineTitle}
          </Text>
          {timeline.timeline_events.map((event, idx) => (
            <View key={idx} style={[styles.timelineItem, { borderColor: event.status === 'ACTIVE' ? colors.brandCyan : colors.borderSubtle }]}>
              <View style={[styles.row, { marginBottom: 2 }]}>
                <Text style={{ color: colors.textPrimary, fontWeight: '600', fontSize: 13, flex: 1 }}>{event.title}</Text>
                <Badge label={SLA_STATUS_LABEL[event.status] ?? event.status} variant={event.status === 'OVERDUE' ? 'danger' : event.status === 'ACTIVE' ? 'info' : 'brand'} />
              </View>
              <Text style={{ color: colors.textSecondary, fontSize: 12 }}>
                {event.instructions} Deadline: {event.deadline_date}
              </Text>
            </View>
          ))}
        </Card>
      )}

      {/* ADR-011: the denial turns on clinical judgment (machine-derived signal only). */}
      {result?.clinical_review?.requires_clinical_interpretation && (
        <Card style={{ marginVertical: spacing.sm }}>
          <View style={{ flexDirection: 'row', gap: spacing.xs, flexWrap: 'wrap' }}>
            <Badge label="Clinical review required" variant="warning" />
            <Badge label="Machine-derived" variant="info" />
          </View>
          {result.clinical_review.reasons.map((reason) => (
            <Text key={reason} style={{ color: colors.textPrimary, fontSize: typography.sizes.sm, marginTop: spacing.xs }}>
              • {reason}
            </Text>
          ))}
          <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs, marginTop: spacing.xs }}>
            {result.clinical_review.note}
          </Text>
          {!caseId && (
            <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs, marginTop: spacing.xs }}>
              Scan your denial letter to create a case, then request a statement from a named doctor here.
            </Text>
          )}
        </Card>
      )}
      {result && (
        <ClinicalReviewCard
          caseId={caseId}
          sourceModule="bimanyay"
          trigger={result.clinical_review?.requires_clinical_interpretation ? 'DENIAL_CATEGORY' : 'MANUAL'}
          recommendationReason={result.clinical_review?.reasons.join(' ') || null}
          insurerName={insurerName}
          processing={processing}
        />
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { paddingBottom: 40 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  title: { fontWeight: '700' },
  desc: { lineHeight: 22 },
  cardTitle: { fontWeight: '600', fontSize: 16 },
  input: { borderWidth: 1, borderRadius: 8, padding: 10, fontSize: 14, marginBottom: 8 },
  halfInput: { flex: 1, marginRight: 8 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  timelineItem: { borderLeftWidth: 3, paddingLeft: 10, paddingVertical: 8, marginBottom: 6 },
});
