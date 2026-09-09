import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TextInput } from 'react-native';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { Card, Button, Badge } from '../components';
import { api, DaaviSetuClaimResponse, ApiError } from '../api';

export const DaaviSetuScreen: React.FC = () => {
  const { colors, spacing, typography } = useTheme();
  const { t } = useLanguage();

  // Form state
  const [patientName, setPatientName] = useState('Viraj Jadhao');
  const [policyId, setPolicyId] = useState('POL-STAR-774411');

  // Result state
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DaaviSetuClaimResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Create case (needed for DaaviSetu endpoint)
      const caseRes = await api.kadi.createCase({ consent_opt_in: true });

      // 2. Upload minimal document to populate case context
      await api.kadi.uploadDocument(caseRes.id, {
        uri: 'data:text/plain;base64,',
        name: 'treatment.txt',
        type: 'text/plain',
      });

      // 3. Generate pre-auth package
      const claimRes = await api.daavisetu.submitClaim(caseRes.id, {
        policy_number: policyId,
        patient_name: patientName,
      });
      setResult(claimRes);
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.message || 'Failed to generate pre-auth package.');
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
          📋 {t.modules.daavisetu.title}
        </Text>
        <Badge label="Pre-Auth" variant="brand" />
      </View>

      <Text style={[styles.desc, { color: colors.textSecondary, fontSize: typography.sizes.sm, marginBottom: spacing.md }]}>
        {t.modules.daavisetu.desc}
      </Text>

      {/* Input Form */}
      <Card style={{ marginBottom: spacing.md }}>
        <Text style={[styles.cardTitle, { color: colors.textPrimary, marginBottom: spacing.sm }]}>
          Pre-Authorization Details
        </Text>

        <TextInput style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]} placeholder="Patient Full Name" placeholderTextColor={colors.textMuted} value={patientName} onChangeText={setPatientName} />
        <TextInput style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]} placeholder="Health Policy ID" placeholderTextColor={colors.textMuted} value={policyId} onChangeText={setPolicyId} />

        {error && <Text style={{ color: '#ef4444', fontSize: 13, marginBottom: 8 }}>⚠️ {error}</Text>}

        <Button
          title={loading ? 'Generating...' : '📄 Auto-Fill Pre-Authorization'}
          onPress={handleGenerate}
          variant="primary"
          disabled={loading}
        />
      </Card>

      {/* Result */}
      {result && (
        <Card>
          <View style={[styles.row, { marginBottom: spacing.sm }]}>
            <Text style={{ color: colors.textPrimary, fontWeight: '700', fontSize: typography.sizes.md, flex: 1 }}>
              ✓ Generated Pre-Auth Package
            </Text>
            <Badge label={result.claim_id} variant="info" />
          </View>

          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>Patient:</Text>
            <Text style={[styles.fieldValue, { color: colors.textPrimary }]}>{result.form_data.patient_name}</Text>
          </View>
          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>Policy:</Text>
            <Text style={[styles.fieldValue, { color: colors.textPrimary }]}>{result.form_data.policy_number}</Text>
          </View>
          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>Hospital:</Text>
            <Text style={[styles.fieldValue, { color: colors.textPrimary }]}>{result.form_data.hospital_name}</Text>
          </View>
          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>Diagnosis:</Text>
            <Text style={[styles.fieldValue, { color: colors.textPrimary }]}>{result.form_data.diagnosis}</Text>
          </View>
          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>Treatment:</Text>
            <Text style={[styles.fieldValue, { color: colors.textPrimary }]}>{result.form_data.treatment_plan}</Text>
          </View>
          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>Cost:</Text>
            <Text style={[styles.fieldValue, { color: colors.textPrimary }]}>₹{result.form_data.estimated_cost.toLocaleString('en-IN')}</Text>
          </View>

          <View style={[styles.statusBar, { borderColor: '#22c55e' }]}>
            <Text style={{ color: '#22c55e', fontSize: 13 }}>
              Status: {result.status === 'ready_for_review' ? '✓ Ready for Review' : result.status}
            </Text>
          </View>
        </Card>
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
  fieldRow: { flexDirection: 'row', paddingVertical: 4 },
  fieldLabel: { color: '#9ca3af', fontSize: 13, width: 80 },
  fieldValue: { fontSize: 13, fontWeight: '600', flex: 1 },
  statusBar: { borderLeftWidth: 3, paddingLeft: 10, paddingVertical: 8, marginTop: 12 },
});
