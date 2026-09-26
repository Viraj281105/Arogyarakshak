import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, TextInput, Linking, Alert } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList, BottomTabParamList } from '../navigation/types';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { Card, Button, Badge, ResolutionReviewCard, ReadinessCard } from '../components';
import { api, DaaviSetuClaimResponse, ApiError } from '../api';
import { getCaseAccessToken } from '../api/caseAuth';
import { useOfflineQueue } from '../hooks/useOfflineQueue';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { useSSEStream } from '../hooks/useSSEStream';
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
  // Empty by default: pre-filled values were submitted verbatim by users who did not
  // edit them, producing determinations about a fabricated person.
  const [patientName, setPatientName] = useState('');
  const [policyId, setPolicyId] = useState('');
  const [hospitalName, setHospitalName] = useState('');
  const [treatmentPlan, setTreatmentPlan] = useState('');

  // Case & Result state
  const [caseId, setCaseId] = useState<string | null>(route.params?.caseId || null);
  // The scan hands over a case whose OCR/extraction is still running server-side;
  // case-derived cards wait for it instead of reading a half-built case.
  const sse = useSSEStream(caseId || undefined);
  const processing = sse.isStreaming && !sse.isCompleted;
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
        // A case is only ever created from the scan flow, where consent is captured.
        // Creating one here would grant consent the patient never gave.
        throw new Error(t.scanner.scanFirst);
      }

      // Generate pre-auth package with comprehensive form details
      const claimRes = await api.daavisetu.submitClaim(activeCaseId, claimData);
      setResult(claimRes);
    } catch (err) {
      const apiErr = err as ApiError;
      let queuedId: string | null = null;
      if (activeCaseId) {
        queuedId = await enqueueAction('SUBMIT_PREAUTH', {
          caseId: activeCaseId,
          claimData,
        });
        setOfflineQueued(!!queuedId);
      }
      if (activeCaseId && !queuedId) {
        setError('Could not save this for offline retry — please try again when back online.');
      } else {
        setError(
          !isOnline
            ? 'Device is offline. Pre-authorization request queued; will sync automatically when reconnected.'
            : `${apiErr.message || 'Failed to generate pre-auth package.'}${queuedId ? ' (Queued for offline retry)' : ''}`
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!caseId) return;
    // SEC-08: this opens the PDF in the device's external browser/viewer via
    // Linking.openURL, which cannot attach a custom X-Case-Access-Token header the way
    // apiClient normally does — the request was previously unauthenticated and always
    // failed with 401. The token is passed as a query parameter instead (SEC-07:
    // query-string tokens are accepted ONLY for safe, read-only GET requests like this
    // one — never for a state-changing request), matching the same mechanism the SSE
    // stream already uses for the identical reason.
    const token = getCaseAccessToken(caseId);
    if (!token) {
      setError('Missing this case\'s access token — cannot download the PDF. Re-open the case from a fresh scan.');
      return;
    }
    const pdfUrl = `${ENV.API_BASE_URL}/api/v1/daavisetu/cases/${caseId}/claim/pdf?access_token=${encodeURIComponent(token)}`;
    try {
      const supported = await Linking.canOpenURL(pdfUrl);
      if (supported) {
        await Linking.openURL(pdfUrl);
      }
    } catch (e) {
      console.warn('Cannot open PDF URL:', e);
    }
  };

  // Downloads the full claim package ZIP (#81): pre-auth PDF + redacted case-summary
  // excerpt + a manifest disclosing what is and is not included. Same query-token
  // pattern as the PDF download above — Linking.openURL cannot attach a custom header.
  const handleDownloadPackage = async () => {
    if (!caseId) return;
    const token = getCaseAccessToken(caseId);
    if (!token) {
      setError('Missing this case\'s access token — cannot download the package. Re-open the case from a fresh scan.');
      return;
    }
    const zipUrl = `${ENV.API_BASE_URL}/api/v1/daavisetu/cases/${caseId}/claim/package?access_token=${encodeURIComponent(token)}`;
    try {
      const supported = await Linking.canOpenURL(zipUrl);
      if (supported) {
        await Linking.openURL(zipUrl);
      }
    } catch (e) {
      console.warn('Cannot open claim package URL:', e);
    }
  };

  // SEC-03: same pattern as BillNyayScreen's handleDeleteCase — the server also
  // purges a case automatically once its retention deadline passes, but this lets
  // the patient ask for real erasure (DELETE /cases/{id}, P1-10) right now.
  const handleDeleteCase = () => {
    if (!caseId) return;
    Alert.alert(
      t.common.deleteCaseConfirmTitle,
      t.common.deleteCaseConfirmBody,
      [
        { text: t.common.cancel, style: 'cancel' },
        {
          text: t.common.delete,
          style: 'destructive',
          onPress: async () => {
            try {
              await api.kadi.deleteCase(caseId);
              setCaseId(null);
              setResult(null);
              setError(null);
            } catch (err) {
              const apiErr = err as ApiError;
              setError(apiErr.message || 'Failed to delete this case.');
            }
          },
        },
      ]
    );
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
            onPress={() => navigation.navigate('CameraScan', { documentType: 'general', returnTo: 'DaaviSetu' })}
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
            <View style={{ marginTop: spacing.sm, gap: spacing.xs }}>
              <Button
                title={m.downloadPdf}
                onPress={handleDownloadPdf}
                variant="outline"
              />
              <Button
                title={m.downloadPackage}
                onPress={handleDownloadPackage}
                variant="outline"
              />
            </View>
          )}
        </Card>
      )}

      {caseId && (
        <View style={{ alignItems: 'flex-end', marginBottom: spacing.md }}>
          <Button
            title={t.common.deleteCaseBtn}
            onPress={handleDeleteCase}
            variant="outline"
            size="sm"
          />
        </View>
      )}

      <ResolutionReviewCard caseId={caseId} refreshToken={sse.isCompleted} />
      <ReadinessCard caseId={caseId} processing={processing} />
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
