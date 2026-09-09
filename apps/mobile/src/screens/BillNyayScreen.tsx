import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList, BottomTabParamList } from '../navigation/types';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { Card, Button, Badge, AgentStreamVisualizer } from '../components';
import { api, BillNyayAuditResponse, ApiError } from '../api';
import { useSSEStream } from '../hooks/useSSEStream';

type NavigationProp = NativeStackNavigationProp<RootStackParamList>;
type BillNyayRouteProp = RouteProp<BottomTabParamList, 'BillNyay'>;

export const BillNyayScreen: React.FC = () => {
  const navigation = useNavigation<NavigationProp>();
  const route = useRoute<BillNyayRouteProp>();
  const { colors, spacing, typography } = useTheme();
  const { t } = useLanguage();
  const m = t.modules.billnyay;

  const [loading, setLoading] = useState(false);
  const [auditResult, setAuditResult] = useState<BillNyayAuditResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [caseId, setCaseId] = useState<string | null>(route.params?.caseId || null);

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
        // Create a case session in Kadi if one does not exist
        const caseRes = await api.kadi.createCase({ consent_opt_in: true });
        activeId = caseRes.id || caseRes.case_id || null;
        setCaseId(activeId);
      }

      if (!activeId) {
        throw new Error('Unable to initialize active Kadi case session.');
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
          <Text style={{ color: colors.brandCyan, fontSize: typography.sizes.xs, fontWeight: '600' }}>
            {m.activeCaseReady} (Case: {caseId.slice(0, 8)}...)
          </Text>
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

          {auditResult.audit_items.map((item, idx) => (
            <View
              key={idx}
              style={[styles.auditItem, { borderColor: item.is_deviation ? '#ef4444' : '#22c55e', borderLeftWidth: 3 }]}
            >
              <Text style={{ color: colors.textPrimary, fontWeight: '600', marginBottom: 2 }}>
                {item.item_name}
              </Text>
              <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>
                {m.charged}: ₹{item.charged} | {m.cghsCap}: ₹{item.cghs_benchmark}
                {item.is_deviation ? ` | +${item.deviation_percentage}%` : ` | ${m.fair}`}
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
  activeCaseNotice: { borderWidth: 1, borderRadius: 6, paddingHorizontal: 12, paddingVertical: 6, marginTop: 8 },
  cardTitle: { fontWeight: '600' },
  cardBody: { lineHeight: 20 },
  statsRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  statItem: { alignItems: 'center', flex: 1 },
  auditItem: { paddingVertical: 8, paddingHorizontal: 12, marginVertical: 4, borderRadius: 6, backgroundColor: 'rgba(255,255,255,0.03)' },
});
