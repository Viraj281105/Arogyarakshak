import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TextInput } from 'react-native';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { Card, Button, Badge } from '../components';
import { api, SchemeResult, ApiError } from '../api';
import { useOfflineQueue } from '../hooks/useOfflineQueue';
import { useNetworkStatus } from '../hooks/useNetworkStatus';

export const SchemeSetuScreen: React.FC = () => {
  const { colors, spacing, typography } = useTheme();
  const { t } = useLanguage();
  const { enqueueAction } = useOfflineQueue();
  const { isOnline } = useNetworkStatus();
  const m = t.modules.schemesetu;

  // Form state
  const [income, setIncome] = useState('120000');
  const [state, setState] = useState('Maharashtra');
  const [category, setCategory] = useState('General');
  const [medicalNeed, setMedicalNeed] = useState('Heart bypass surgery (CABG)');

  // Result state
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SchemeResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [offlineQueued, setOfflineQueued] = useState(false);

  const handleCheck = async () => {
    setLoading(true);
    setError(null);
    setOfflineQueued(false);

    const payload = {
      income: parseFloat(income) || 0,
      location_state: state,
      category,
      medical_need: medicalNeed,
    };

    try {
      const data = await api.schemesetu.checkEligibility(payload);
      setResults(data);
    } catch (err) {
      const apiErr = err as ApiError;
      await enqueueAction('CHECK_SCHEME', payload);
      setOfflineQueued(true);
      setError(
        !isOnline
          ? 'Device is offline. Eligibility check queued; will sync automatically when reconnected.'
          : `${apiErr.message || 'Failed to check eligibility.'} (Queued for offline retry)`
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.bgBase }]}
      contentContainerStyle={[styles.content, { padding: spacing.md }]}
    >
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.textPrimary, fontSize: typography.sizes.xl }]}>
          🏛️ {m.title}
        </Text>
        <Badge label={m.statutory} variant="success" />
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
          placeholder={m.income}
          keyboardType="numeric"
          placeholderTextColor={colors.textMuted}
          value={income}
          onChangeText={setIncome}
        />
        <TextInput
          style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
          placeholder={m.state}
          placeholderTextColor={colors.textMuted}
          value={state}
          onChangeText={setState}
        />
        <TextInput
          style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
          placeholder={m.category}
          placeholderTextColor={colors.textMuted}
          value={category}
          onChangeText={setCategory}
        />
        <TextInput
          style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
          placeholder={m.medicalNeed}
          placeholderTextColor={colors.textMuted}
          value={medicalNeed}
          onChangeText={setMedicalNeed}
        />

        {error && <Text style={{ color: '#ef4444', fontSize: 13, marginBottom: 8 }}>⚠️ {error}</Text>}

        <Button
          title={loading ? m.checking : m.checkBtn}
          onPress={handleCheck}
          variant="primary"
          disabled={loading}
        />
      </Card>

      {/* Results */}
      {results && results.map((scheme, idx) => {
        const isEligible = scheme.estimated_eligibility === 'eligible';
        return (
          <Card key={idx} style={{ marginBottom: spacing.sm }}>
            <View style={[styles.row, { marginBottom: spacing.xs }]}>
              <Text style={{ color: isEligible ? '#22c55e' : colors.textSecondary, fontWeight: '700', fontSize: typography.sizes.md, flex: 1 }}>
                {scheme.scheme_name}
              </Text>
              <Badge
                label={isEligible ? `${(scheme.confidence_score * 100).toFixed(0)}% ${m.match}` : m.notEligible}
                variant={isEligible ? 'success' : 'danger'}
              />
            </View>

            <Text style={{ color: colors.textSecondary, fontSize: 13, lineHeight: 20, marginBottom: spacing.xs }}>
              {scheme.reason}
            </Text>

            {isEligible && scheme.claim_guide_steps.length > 0 && (
              <View style={{ marginTop: spacing.xs }}>
                <Text style={{ color: colors.textPrimary, fontWeight: '600', fontSize: 13, marginBottom: 4 }}>
                  {m.howToClaim}
                </Text>
                {scheme.claim_guide_steps.map((step, sIdx) => (
                  <Text key={sIdx} style={{ color: colors.textSecondary, fontSize: 12, lineHeight: 18, paddingLeft: 8 }}>
                    {sIdx + 1}. {step}
                  </Text>
                ))}
              </View>
            )}
          </Card>
        );
      })}

      {results && results.length === 0 && (
        <Text style={{ color: colors.textSecondary, textAlign: 'center', marginTop: spacing.md }}>
          {m.noMatches}
        </Text>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { paddingBottom: 40 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  title: { fontWeight: '700', flex: 1 },
  desc: { lineHeight: 22 },
  cardTitle: { fontWeight: '600', fontSize: 16 },
  input: { borderWidth: 1, borderRadius: 8, padding: 10, fontSize: 14, marginBottom: 8 },
  row: { flexDirection: 'row', alignItems: 'center' },
});
