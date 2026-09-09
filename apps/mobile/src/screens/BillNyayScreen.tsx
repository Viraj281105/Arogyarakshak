import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { Card, Button, Badge } from '../components';
import { api, BillNyayAuditResponse, ApiError } from '../api';

type NavigationProp = NativeStackNavigationProp<RootStackParamList>;

export const BillNyayScreen: React.FC = () => {
  const navigation = useNavigation<NavigationProp>();
  const { colors, spacing, typography } = useTheme();
  const { t } = useLanguage();

  const [loading, setLoading] = useState(false);
  const [auditResult, setAuditResult] = useState<BillNyayAuditResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [caseId, setCaseId] = useState<string | null>(null);

  const handleStartAudit = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Create case
      const caseRes = await api.kadi.createCase({ consent_opt_in: true });
      setCaseId(caseRes.id);

      // 2. Navigate to camera to capture bill, then audit
      // For now, run a simulated upload and audit flow
      const formData = new FormData();
      formData.append('file', {
        uri: 'data:text/plain;base64,Q29uc3VsdGF0aW9uOiA1MDAKV2FyZCBTdGF5OiAyNTAwClRvdGFsOiAzMDAw',
        name: 'bill.txt',
        type: 'text/plain',
      } as any);

      await api.kadi.uploadDocument(caseRes.id, {
        uri: 'data:text/plain;base64,',
        name: 'bill.txt',
        type: 'text/plain',
      });

      // 3. Run audit
      const result = await api.billnyay.audit(caseRes.id);
      setAuditResult(result);
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.message || 'Failed to run bill audit.');
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
          ⚖️ {t.modules.billnyay.title}
        </Text>
        <Badge label={t.modules.billnyay.statutory} variant="info" />
      </View>

      <Text style={[styles.desc, { color: colors.textSecondary, fontSize: typography.sizes.sm }]}>
        {t.modules.billnyay.desc}
      </Text>

      <Card style={{ marginVertical: spacing.md }}>
        <Text style={[styles.cardTitle, { color: colors.textPrimary, fontSize: typography.sizes.md }]}>
          Hospital Discharge Bill Audit
        </Text>
        <Text style={[styles.cardBody, { color: colors.textSecondary, fontSize: typography.sizes.sm, marginVertical: spacing.sm }]}>
          Scan any IPD/OPD hospital bill to detect inflated room rent charges, unbundled surgical consumables, and tariff rates exceeding the official CGHS 2024 benchmarks.
        </Text>

        {error && (
          <Text style={{ color: '#ef4444', fontSize: typography.sizes.sm, marginBottom: spacing.sm }}>
            ⚠️ {error}
          </Text>
        )}

        <Button
          title={loading ? 'Auditing...' : t.modules.billnyay.cta}
          onPress={handleStartAudit}
          variant="primary"
          style={{ marginTop: spacing.xs }}
          disabled={loading}
        />
      </Card>

      {/* Audit Results */}
      {auditResult && (
        <Card style={{ marginVertical: spacing.sm }}>
          <Text style={[styles.cardTitle, { color: colors.textPrimary, fontSize: typography.sizes.md, marginBottom: spacing.sm }]}>
            Audit Results
          </Text>

          <View style={styles.statsRow}>
            <View style={styles.statItem}>
              <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>Charged</Text>
              <Text style={{ color: colors.textPrimary, fontSize: typography.sizes.md, fontWeight: '700' }}>
                ₹{auditResult.total_charged.toLocaleString('en-IN')}
              </Text>
            </View>
            <View style={styles.statItem}>
              <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>CGHS Cap</Text>
              <Text style={{ color: colors.brandCyan, fontSize: typography.sizes.md, fontWeight: '700' }}>
                ₹{auditResult.total_benchmark.toLocaleString('en-IN')}
              </Text>
            </View>
            <View style={styles.statItem}>
              <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>Flagged</Text>
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
                Charged: ₹{item.charged} | CGHS: ₹{item.cghs_benchmark}
                {item.is_deviation ? ` | +${item.deviation_percentage}%` : ' | ✓ Fair'}
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
  cardTitle: { fontWeight: '600' },
  cardBody: { lineHeight: 20 },
  statsRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  statItem: { alignItems: 'center', flex: 1 },
  auditItem: { paddingVertical: 8, paddingHorizontal: 12, marginVertical: 4, borderRadius: 6, backgroundColor: 'rgba(255,255,255,0.03)' },
});
