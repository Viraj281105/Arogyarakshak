import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TextInput, Alert, Share } from 'react-native';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { Card, Button, Badge } from '../components';
import { api, BimaNyayAnalysisResponse, BimaNyayTimelineResponse, ApiError } from '../api';
import { useOfflineQueue } from '../hooks/useOfflineQueue';
import { useNetworkStatus } from '../hooks/useNetworkStatus';

export const BimaNyayScreen: React.FC = () => {
  const { colors, spacing, typography } = useTheme();
  const { t, language } = useLanguage();
  const { enqueueAction } = useOfflineQueue();
  const { isOnline } = useNetworkStatus();
  const m = t.modules.bimanyay;

  // Form state
  const [policyNumber, setPolicyNumber] = useState('POL-884422');
  const [insurerName, setInsurerName] = useState('Star Health Insurance');
  const [policyAge, setPolicyAge] = useState('6');
  const [claimedAmount, setClaimedAmount] = useState('180000');
  const [deniedAmount, setDeniedAmount] = useState('180000');
  const [denialCategory, setDenialCategory] = useState('PED_NON_DISCLOSURE');
  const [denialReason, setDenialReason] = useState('Pre-existing condition non-disclosure');
  const [diagnosis, setDiagnosis] = useState('Acute Myocardial Infarction');

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
      const analysisResult = await api.bimanyay.analyze(analysisPayload, language);
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
      await enqueueAction('ANALYZE_DENIAL', {
        data: analysisPayload,
        language,
      });
      setOfflineQueued(true);
      setError(
        !isOnline
          ? 'Device is offline. Denial audit queued; will sync automatically when reconnected.'
          : `${apiErr.message || 'Failed to analyze denial.'} (Queued for offline retry)`
      );
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
                <Badge label={event.status} variant={event.status === 'ACTIVE' ? 'info' : 'brand'} />
              </View>
              <Text style={{ color: colors.textSecondary, fontSize: 12 }}>
                {event.instructions} Deadline: {event.deadline_date}
              </Text>
            </View>
          ))}
        </Card>
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
