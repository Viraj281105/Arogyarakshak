import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert, Share, Linking } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList, BottomTabParamList } from '../navigation/types';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import {
  Card,
  Button,
  Badge,
  AgentStreamVisualizer,
  ResolutionReviewCard,
  ClinicalReviewCard,
  SafetyNotice,
  StatementView,
} from '../components';
import { api, BillNyayAuditResponse, BillNyayAppealResponse, ApiError, PlausibilityResponse } from '../api';
import { getCaseAccessToken } from '../api/caseAuth';
import { useSSEStream } from '../hooks/useSSEStream';
import { ENV } from '../config/env';

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
  const [caseId, setCaseId] = useState<string | null>(route.params?.caseId || null);

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

  const sse = useSSEStream(caseId || undefined);

  useEffect(() => {
    if (route.params?.caseId) {
      setCaseId(route.params.caseId || null);
      // Auto-trigger audit if coming directly from completed scan
      if (route.params.scanCompleted) {
        handleRunAudit(route.params.caseId);
      }
    }
  }, [route.params?.caseId, route.params?.scanCompleted]);

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
              setCaseId(null);
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

  // Downloads the exact signed PDF the appeal drafted (#66) — served from stored
  // bytes, never regenerated, so it always matches what was hashed and signed.
  // Same query-token pattern as DaaviSetu's PDF download: Linking.openURL cannot
  // attach a custom header, so the one-time case access token travels as a
  // query parameter on this safe, read-only GET.
  const handleDownloadAppealPdf = async () => {
    if (!caseId) return;
    const token = getCaseAccessToken(caseId);
    if (!token) {
      setAppealError('Missing this case\'s access token — cannot download the PDF. Re-open the case from a fresh scan.');
      return;
    }
    const pdfUrl = `${ENV.API_BASE_URL}/api/v1/billnyay/cases/${caseId}/appeal/pdf?access_token=${encodeURIComponent(token)}`;
    try {
      const supported = await Linking.canOpenURL(pdfUrl);
      if (supported) {
        await Linking.openURL(pdfUrl);
      }
    } catch (e) {
      console.warn('Cannot open appeal PDF URL:', e);
    }
  };

  const handleShareAppeal = async () => {
    if (!appealResult) return;
    try {
      await Share.share({ message: appealResult.appeal_letter });
    } catch (e) {
      console.warn('Cannot share appeal letter:', e);
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

      {caseId && (sse.isStreaming || sse.progress > 0) && (
        <AgentStreamVisualizer
          progress={sse.progress}
          latestEvent={sse.latestEvent}
          isStreaming={sse.isStreaming}
          isCompleted={sse.isCompleted}
          error={sse.error}
        />
      )}

      <ResolutionReviewCard caseId={caseId} refreshToken={sse.isCompleted} />

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
            disabled={loading}
          />

          {caseId && (
            <Button
              title={appealLoading ? m.drafting : m.draftAppealBtn}
              onPress={handleDraftAppeal}
              variant="outline"
              disabled={appealLoading}
            />
          )}
        </View>
      </Card>

      {/* Audit Results */}
      {auditResult && (
        <Card style={{ marginVertical: spacing.sm }}>
          <Text style={[styles.cardTitle, { color: colors.textPrimary, fontSize: typography.sizes.md, marginBottom: spacing.sm }]}>
            {m.auditResults}
          </Text>

          <View style={styles.statsRow}>
            <View style={styles.statItem}>
              <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>{m.charged}</Text>
              <Text style={{ color: colors.textPrimary, fontSize: typography.sizes.md, fontWeight: '700' }}>
                ₹{auditResult.total_charged.toLocaleString('en-IN')}
              </Text>
            </View>
            <View style={styles.statItem}>
              <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>{m.cghsCap}</Text>
              <Text style={{ color: colors.brandCyan, fontSize: typography.sizes.md, fontWeight: '700' }}>
                ₹{auditResult.total_benchmark.toLocaleString('en-IN')}
              </Text>
            </View>
            <View style={styles.statItem}>
              <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>{m.flagged}</Text>
              <Text style={{ color: '#ef4444', fontSize: typography.sizes.md, fontWeight: '700' }}>
                {auditResult.deviations_count}
              </Text>
            </View>
          </View>

          {auditResult.unmatched_count > 0 && (
            <Text
              style={{
                color: '#f59e0b',
                fontSize: typography.sizes.xs,
                marginBottom: spacing.sm,
              }}
            >
              {m.unmatchedNotice
                .replace('{count}', String(auditResult.unmatched_count))
                .replace('{amount}', auditResult.unmatched_amount.toLocaleString('en-IN'))}
            </Text>
          )}

          {auditResult.audit_items.map((item, idx) => {
            // An item with no CGHS counterpart is unverified, not fair.
            const benchmarked = item.benchmarked && item.cghs_benchmark !== null;
            const borderColor = !benchmarked
              ? '#f59e0b'
              : item.is_deviation
              ? '#ef4444'
              : '#22c55e';
            return (
              <View
                key={idx}
                style={[styles.auditItem, { borderColor, borderLeftWidth: 3 }]}
              >
                <Text style={{ color: colors.textPrimary, fontWeight: '600', marginBottom: 2 }}>
                  {item.item_name}
                </Text>
                <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>
                  {m.charged}: ₹{item.charged}
                  {benchmarked
                    ? ` | ${m.cghsCap}: ₹${item.cghs_benchmark}${
                        item.is_deviation ? ` | +${item.deviation_percentage}%` : ` | ${m.fair}`
                      }`
                    : ` | ${m.notBenchmarked}`}
                </Text>
              </View>
            );
          })}
        </Card>
      )}

      {/* Appeal Letter (5-agent pipeline, #18) */}
      {appealError && (
        <Text style={{ color: '#ef4444', fontSize: typography.sizes.sm, marginTop: spacing.sm }}>
          ⚠️ {appealError}
        </Text>
      )}

      {appealResult && (
        <Card style={{ marginVertical: spacing.sm }}>
          <View style={[styles.header, { marginBottom: spacing.sm }]}>
            <Text style={[styles.cardTitle, { color: colors.textPrimary, fontSize: typography.sizes.md }]}>
              {m.appealTitle}
            </Text>
            <Badge
              label={appealResult.status === 'approve' ? m.appealApprove : m.appealNeedsRevision}
              variant={appealResult.status === 'approve' ? 'success' : 'warning'}
            />
          </View>

          {!appealResult.llm_backed && (
            <Text style={{ color: '#f59e0b', fontSize: typography.sizes.xs, marginBottom: spacing.sm }}>
              {m.appealTemplateNotice}
            </Text>
          )}
          {appealResult.llm_backed && (
            <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs, marginBottom: spacing.sm }}>
              {m.appealLlmBacked}
            </Text>
          )}
          {!appealResult.denial_facts_extracted && (
            <Text style={{ color: '#f59e0b', fontSize: typography.sizes.xs, marginBottom: spacing.sm }}>
              {m.appealFactsNotExtracted}
            </Text>
          )}

          <Text
            style={{ color: colors.textPrimary, fontSize: typography.sizes.sm, lineHeight: 20, marginBottom: spacing.sm }}
          >
            {appealResult.appeal_letter}
          </Text>

          {/* ADR-011: attached verbatim when it exists; its absence is stated, never implied away. */}
          {appealResult.human_clinical_statement_attached ? (
            appealResult.clinical_statements.map((s) => <StatementView key={s.statement_id} statement={s} />)
          ) : (
            <Text style={{ color: colors.statusWarning, fontSize: typography.sizes.xs, marginBottom: spacing.sm }}>
              No statement from a named clinician is attached. Clinical reasoning in this letter is general,
              software-drafted reasoning — not a doctor&apos;s opinion. (This note is for you; it is not in the PDF.)
            </Text>
          )}
          <Text style={{ color: colors.textMuted, fontSize: typography.sizes.xs, marginBottom: spacing.sm }}>
            The PDF is re-generated whenever a clinician&apos;s statement changes — download it again right before sending.
          </Text>

          <View style={{ gap: spacing.xs }}>
            <Button title={m.downloadAppealPdf} onPress={handleDownloadAppealPdf} variant="outline" />
            <Button title={m.shareAppealBtn} onPress={handleShareAppeal} variant="outline" />
          </View>
        </Card>
      )}

      {caseId && (
        <Card style={{ marginVertical: spacing.sm }}>
          <Button title="🩺 Check clinical plausibility" onPress={handleCheckPlausibility} variant="outline" size="sm" />
          {plausibility && (
            <View style={{ marginTop: spacing.sm, gap: spacing.xs }}>
              <View style={{ flexDirection: 'row', gap: spacing.xs, flexWrap: 'wrap' }}>
                <Badge label="Machine-derived" variant="info" />
                <Badge
                  label={plausibility.assessment.status.replaceAll('_', ' ')}
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
      )}
      <SafetyNotice caseId={caseId} refreshToken={sse.isCompleted} />
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
  statsRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  statItem: { alignItems: 'center', flex: 1 },
  auditItem: { paddingVertical: 8, paddingHorizontal: 12, marginVertical: 4, borderRadius: 6, backgroundColor: 'rgba(255,255,255,0.03)' },
});
