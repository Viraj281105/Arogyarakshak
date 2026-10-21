import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList, BottomTabParamList } from '../navigation/types';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import {
  Card,
  Button,
  Badge,
  ProcessingStatusCard,
  ResolutionReviewCard,
  ClinicalReviewCard,
  SafetyNotice,
} from '../components';
import { api, BillNyayAuditResponse, BillNyayAppealResponse, ApiError, PlausibilityResponse } from '../api';
import { useCaseProcessing } from '../hooks/useCaseProcessing';
import { useActiveCaseId } from '../hooks/useActiveCase';
import { clearActiveCase, resolveCaseId } from '../services/activeCase';
import { AppealCard } from './billnyay/AppealCard';
import { AuditResultsCard } from './billnyay/AuditResultsCard';
import { PlausibilityCard } from './billnyay/PlausibilityCard';

type NavigationProp = NativeStackNavigationProp<RootStackParamList>;
type BillNyayRouteProp = RouteProp<BottomTabParamList, 'BillNyay'>;

export const BillNyayScreen: React.FC = () => {
  const navigation = useNavigation<NavigationProp>();
  const route = useRoute<BillNyayRouteProp>();
  const { colors, spacing, typography } = useTheme();
  const { t, language } = useLanguage();
  const m = t.modules.billnyay;

  const [loading, setLoading] = useState(false);
  const [auditResult, setAuditResult] = useState<BillNyayAuditResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  // The scan that brought the patient here, else the case they are working on in
  // another tab. A case deleted from this screen is dropped immediately.
  const activeCaseId = useActiveCaseId();
  const [deletedCaseId, setDeletedCaseId] = useState<string | null>(null);
  const resolvedCaseId = resolveCaseId(route.params?.caseId, activeCaseId);
  const caseId = resolvedCaseId && resolvedCaseId !== deletedCaseId ? resolvedCaseId : null;

  const [appealLoading, setAppealLoading] = useState(false);
  const [appealResult, setAppealResult] = useState<BillNyayAppealResponse | null>(null);
  const [plausibility, setPlausibility] = useState<PlausibilityResponse | null>(null);

  // ADR-011: bounded plausibility check (machine-derived, never a necessity verdict).
  const handleCheckPlausibility = async () => {
    if (!caseId) return;
    try {
      setPlausibility(await api.billnyay.plausibility(caseId));
    } catch (err) {
      setError((err as ApiError).detail || (err as ApiError).message);
    }
  };
  const [appealError, setAppealError] = useState<string | null>(null);

  // Processing lifecycle: `ready` only once the server reports extraction finished.
  const proc = useCaseProcessing(caseId);

  // A fresh scan asks for the audit, but it runs only when extraction has finished —
  // auditing straight after the upload 202 audited an empty case.
  const [pendingAuditFor, setPendingAuditFor] = useState<string | null>(null);
  useEffect(() => {
    if (route.params?.caseId && route.params.scanCompleted) {
      setPendingAuditFor(route.params.caseId);
      setAuditResult(null);
      setPlausibility(null);
      setAppealResult(null);
    }
  }, [route.params?.caseId, route.params?.scanCompleted]);
  useEffect(() => {
    if (pendingAuditFor && proc.ready && proc.caseId === pendingAuditFor) {
      setPendingAuditFor(null);
      handleRunAudit(pendingAuditFor);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingAuditFor, proc.ready, proc.caseId]);

  const handleRunAudit = async (targetCaseId?: string) => {
    setLoading(true);
    setError(null);
    try {
      let activeId: string | null = targetCaseId || caseId;
      if (!activeId) {
        // A case is only ever created from the scan flow, where consent is captured.
        // Creating one here would grant consent the patient never gave.
        throw new Error(t.scanner.scanFirst);
      }

      // Execute CGHS 2024 line-item benchmark audit
      const result = await api.billnyay.audit(activeId);
      setAuditResult(result);
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.message || 'Failed to run hospital bill audit.');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenScanner = () => {
    navigation.navigate('CameraScan', { documentType: 'bill' });
  };

  // SEC-03: the server also purges a case automatically once its retention deadline
  // passes (does not depend on the patient coming back), but this lets them ask for
  // deletion right now — the same real erasure DELETE /cases/{id} already performs
  // (P1-10), just reachable from the UI instead of only via a direct API call.
  const handleDeleteCase = () => {
    if (!caseId) return;
    Alert.alert(
      m.deleteCaseConfirmTitle,
      m.deleteCaseConfirmBody,
      [
        { text: t.common.cancel, style: 'cancel' },
        {
          text: t.common.delete,
          style: 'destructive',
          onPress: async () => {
            try {
              await api.kadi.deleteCase(caseId);
              setDeletedCaseId(caseId);
              clearActiveCase(caseId);
              setAuditResult(null);
              setError(null);
              setAppealResult(null);
              setAppealError(null);
            } catch (err) {
              const apiErr = err as ApiError;
              setError(apiErr.message || 'Failed to delete this case.');
            }
          },
        },
      ]
    );
  };

  // Runs the 5-agent appeal pipeline (#18) and persists a signed PDF server-side.
  // Does not require a prior audit — the appeal reads the case's document text
  // directly — so the button is available as soon as a case exists.
  const handleDraftAppeal = async () => {
    if (!caseId) return;
    setAppealLoading(true);
    setAppealError(null);
    try {
      const result = await api.billnyay.appeal(caseId, language);
      setAppealResult(result);
    } catch (err) {
      const apiErr = err as ApiError;
      setAppealError(apiErr.message || 'Failed to draft the appeal letter.');
    } finally {
      setAppealLoading(false);
    }
  };

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.bgBase }]}
      contentContainerStyle={[styles.content, { padding: spacing.md }]}
    >
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.textPrimary, fontSize: typography.sizes.xl }]}>
          ⚖️ {m.title}
        </Text>
        <Badge label={m.statutory} variant="info" />
      </View>

      <Text style={[styles.desc, { color: colors.textSecondary, fontSize: typography.sizes.sm }]}>
        {m.desc}
      </Text>

      {caseId && (
        <View style={[styles.activeCaseNotice, { backgroundColor: 'rgba(6, 182, 212, 0.1)', borderColor: colors.brandCyan }]}>
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
            <Text style={{ color: colors.brandCyan, fontSize: typography.sizes.xs, fontWeight: '600' }}>
              {m.activeCaseReady} (Case: {caseId.slice(0, 8)}...)
            </Text>
            <Button
              title={m.deleteCaseBtn}
              onPress={handleDeleteCase}
              variant="outline"
              size="sm"
            />
          </View>
        </View>
      )}

      <ProcessingStatusCard proc={proc} />

      <ResolutionReviewCard caseId={proc.ready ? caseId : null} refreshToken={proc.ready} />

      <Card style={{ marginVertical: spacing.md }}>
        <Text style={[styles.cardTitle, { color: colors.textPrimary, fontSize: typography.sizes.md }]}>
          {m.cardTitle}
        </Text>
        <Text style={[styles.cardBody, { color: colors.textSecondary, fontSize: typography.sizes.sm, marginVertical: spacing.sm }]}>
          {m.cardBody}
        </Text>

        {error && (
          <Text style={{ color: '#ef4444', fontSize: typography.sizes.sm, marginBottom: spacing.sm }}>
            ⚠️ {error}
          </Text>
        )}

        <View style={{ gap: spacing.xs, marginTop: spacing.xs }}>
          <Button
            title={m.scanBillBtn}
            onPress={handleOpenScanner}
            variant="outline"
            disabled={loading}
          />

          <Button
            title={loading ? m.auditing : m.cta}
            onPress={() => handleRunAudit()}
            variant="primary"
            disabled={loading || (!!caseId && !proc.ready)}
          />

          {caseId && (
            <Button
              title={appealLoading ? m.drafting : m.draftAppealBtn}
              onPress={handleDraftAppeal}
              variant="outline"
              disabled={appealLoading || !proc.ready}
            />
          )}
        </View>
      </Card>

      {/* Audit Results */}
      {auditResult && <AuditResultsCard auditResult={auditResult} />}

      {/* Appeal Letter (5-agent pipeline, #18) */}
      {appealError && (
        <Text style={{ color: '#ef4444', fontSize: typography.sizes.sm, marginTop: spacing.sm }}>
          ⚠️ {appealError}
        </Text>
      )}

      {appealResult && caseId && <AppealCard appealResult={appealResult} caseId={caseId} onError={setAppealError} />}

      {caseId && <PlausibilityCard plausibility={plausibility} ready={proc.ready} onCheck={handleCheckPlausibility} />}
      {/* Only after extraction: an early check would read a half-built case as "no escalation". */}
      <SafetyNotice caseId={proc.ready ? caseId : null} refreshToken={proc.ready} />
      <ClinicalReviewCard
        caseId={caseId}
        sourceModule="billnyay"
        trigger={plausibility?.clinical_review.required ? 'PLAUSIBILITY_FLAG' : 'MANUAL'}
        recommendationReason={plausibility?.assessment.review_reasons.join(' ') || null}
      />
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { paddingBottom: 40 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  title: { fontWeight: '700' },
  desc: { lineHeight: 22 },
  activeCaseNotice: { borderWidth: 1, borderRadius: 6, paddingHorizontal: 12, paddingVertical: 6, marginTop: 8 },
  cardTitle: { fontWeight: '600' },
  cardBody: { lineHeight: 20 },
});
