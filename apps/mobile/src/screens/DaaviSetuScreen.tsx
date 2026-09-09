import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, TextInput, Linking } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList, BottomTabParamList } from '../navigation/types';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { Card, Button, Badge } from '../components';
import { api, DaaviSetuClaimResponse, ApiError } from '../api';
import { useOfflineQueue } from '../hooks/useOfflineQueue';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { ENV } from '../config/env';

type NavigationProp = NativeStackNavigationProp<RootStackParamList>;
type DaaviSetuRouteProp = RouteProp<BottomTabParamList, 'DaaviSetu'>;

export const DaaviSetuScreen: React.FC = () => {
  const navigation = useNavigation<NavigationProp>();
  const route = useRoute<DaaviSetuRouteProp>();
  const { colors, spacing, typography } = useTheme();
  const { t } = useLanguage();
  const { enqueueAction } = useOfflineQueue();
  const { isOnline } = useNetworkStatus();
  const m = t.modules.daavisetu;

  // Form state
  const [patientName, setPatientName] = useState('Viraj Jadhao');
  const [policyId, setPolicyId] = useState('POL-STAR-774411');
  const [hospitalName, setHospitalName] = useState('Apollo Multi-Speciality Hospital, Mumbai');
  const [treatmentPlan, setTreatmentPlan] = useState('Laparoscopic Appendectomy');

  // Case & Result state
  const [caseId, setCaseId] = useState<string | null>(route.params?.caseId || null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DaaviSetuClaimResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [offlineQueued, setOfflineQueued] = useState(false);

  useEffect(() => {
    if (route.params?.caseId) {
      setCaseId(route.params.caseId || null);
    }
  }, [route.params?.caseId]);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setOfflineQueued(false);

    let activeCaseId: string | null = caseId;
    const claimData = {
      policy_number: policyId,
      patient_name: patientName,
      hospital_name: hospitalName,
      treatment_plan: treatmentPlan,
    };

    try {
      if (!activeCaseId) {
        // Initialize case session in Kadi without simulated dummy files
        const caseRes = await api.kadi.createCase({ consent_opt_in: true });
        activeCaseId = caseRes.id || caseRes.case_id || null;
        setCaseId(activeCaseId);
      }

      if (!activeCaseId) {
        throw new Error('Unable to initialize active Kadi case session.');
      }

      // Generate pre-auth package with comprehensive form details
      const claimRes = await api.daavisetu.submitClaim(activeCaseId, claimData);
      setResult(claimRes);
    } catch (err) {
      const apiErr = err as ApiError;
      if (activeCaseId) {
        await enqueueAction('SUBMIT_PREAUTH', {
          caseId: activeCaseId,
          claimData,
        });
        setOfflineQueued(true);
      }
      setError(
        !isOnline
          ? 'Device is offline. Pre-authorization request queued; will sync automatically when reconnected.'
          : `${apiErr.message || 'Failed to generate pre-auth package.'}${activeCaseId ? ' (Queued for offline retry)' : ''}`
      );
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!caseId) return;
    const pdfUrl = `${ENV.API_BASE_URL}/api/v1/daavisetu/cases/${caseId}/claim/pdf`;
    try {
      const supported = await Linking.canOpenURL(pdfUrl);
      if (supported) {
        await Linking.openURL(pdfUrl);
      }
    } catch (e) {
      console.warn('Cannot open PDF URL:', e);
    }
  };

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.bgBase }]}
      contentContainerStyle={[styles.content, { padding: spacing.md }]}
    >
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.textPrimary, fontSize: typography.sizes.xl }]}>
          📋 {m.title}
        </Text>
        <Badge label={m.statutory} variant="brand" />
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
          placeholder={m.patientName}
          placeholderTextColor={colors.textMuted}
          value={patientName}
          onChangeText={setPatientName}
        />
        <TextInput
          style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
          placeholder={m.policyId}
          placeholderTextColor={colors.textMuted}
          value={policyId}
          onChangeText={setPolicyId}
        />
        <TextInput
          style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
          placeholder={m.hospitalName}
          placeholderTextColor={colors.textMuted}
          value={hospitalName}
          onChangeText={setHospitalName}
        />
        <TextInput
          style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
          placeholder={m.treatmentPlan}
          placeholderTextColor={colors.textMuted}
          value={treatmentPlan}
          onChangeText={setTreatmentPlan}
        />

        {error && <Text style={{ color: '#ef4444', fontSize: 13, marginBottom: 8 }}>⚠️ {error}</Text>}

        <View style={{ gap: spacing.xs, marginTop: spacing.xs }}>
          <Button
            title={loading ? m.generating : m.generateBtn}
            onPress={handleGenerate}
            variant="primary"
            disabled={loading}
          />

          <Button
            title="📷 Scan Admission / Policy Slip"
            onPress={() => navigation.navigate('CameraScan', { documentType: 'general' })}
            variant="outline"
          />
        </View>
      </Card>

      {/* Result */}
      {result && (
        <Card>
          <View style={[styles.row, { marginBottom: spacing.sm }]}>
            <Text style={{ color: colors.textPrimary, fontWeight: '700', fontSize: typography.sizes.md, flex: 1 }}>
              {m.generatedTitle}
            </Text>
            <Badge label={result.claim_id} variant="info" />
          </View>

          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>{m.patient}</Text>
            <Text style={[styles.fieldValue, { color: colors.textPrimary }]}>{result.form_data.patient_name}</Text>
          </View>
          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>{m.policy}</Text>
            <Text style={[styles.fieldValue, { color: colors.textPrimary }]}>{result.form_data.policy_number}</Text>
          </View>
          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>{m.hospital}</Text>
            <Text style={[styles.fieldValue, { color: colors.textPrimary }]}>{result.form_data.hospital_name}</Text>
          </View>
          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>{m.diagnosis}</Text>
            <Text style={[styles.fieldValue, { color: colors.textPrimary }]}>{result.form_data.diagnosis}</Text>
          </View>
          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>{m.treatment}</Text>
            <Text style={[styles.fieldValue, { color: colors.textPrimary }]}>{result.form_data.treatment_plan}</Text>
          </View>
          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>{m.cost}</Text>
            <Text style={[styles.fieldValue, { color: colors.textPrimary }]}>₹{result.form_data.estimated_cost.toLocaleString('en-IN')}</Text>
          </View>

          <View style={[styles.statusBar, { borderColor: '#22c55e' }]}>
            <Text style={{ color: '#22c55e', fontSize: 13 }}>
              {m.status} {result.status === 'ready_for_review' ? `✓ ${m.readyForReview}` : result.status}
            </Text>
          </View>

          {caseId && (
            <View style={{ marginTop: spacing.sm }}>
              <Button
                title={m.downloadPdf}
                onPress={handleDownloadPdf}
                variant="outline"
              />
            </View>
          )}
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
