import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useTheme } from '../../theme';
import { useLanguage } from '../../hooks/useLanguage';
import { Card, ExplainToggle } from '../../components';
import { BillNyayAuditResponse } from '../../api';

/** CGHS audit totals, the coverage notice and each line with its explanation trail. An
 *  item with no CGHS counterpart is unverified, never "fair". */
export const AuditResultsCard: React.FC<{ auditResult: BillNyayAuditResponse }> = ({ auditResult }) => {
  const { colors, spacing, typography } = useTheme();
  const m = useLanguage().t.modules.billnyay;
  return (
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
            {(benchmarked ? item.benchmark_basis : item.not_benchmarked_reason) ? (
              <Text style={{ color: colors.textMuted, fontSize: typography.sizes.xs }}>
                {benchmarked ? item.benchmark_basis : item.not_benchmarked_reason}
              </Text>
            ) : null}
            <ExplainToggle explanation={item.explanation} />
          </View>
        );
      })}
    </Card>
  );
};

const styles = StyleSheet.create({
  cardTitle: { fontWeight: '600' },
  statsRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  statItem: { alignItems: 'center', flex: 1 },
  auditItem: { paddingVertical: 8, paddingHorizontal: 12, marginVertical: 4, borderRadius: 6, backgroundColor: 'rgba(255,255,255,0.03)' },
});
