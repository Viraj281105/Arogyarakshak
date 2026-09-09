import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { Card, Button, Badge } from '../components';
import { api, DawaCheckBenchmarkResponse, ApiError } from '../api';

type NavigationProp = NativeStackNavigationProp<RootStackParamList>;

interface QuickSample {
  name: string;
  mrp: string;
}

const QUICK_SAMPLES: QuickSample[] = [
  { name: 'Dolo 650mg Tablet (15s)', mrp: '33.5' },
  { name: 'Augmentin 625 Duo Tablet (10s)', mrp: '220.0' },
  { name: 'Metformin 500mg SR Tablet (10s)', mrp: '18.0' },
  { name: 'Meropenem 1g Injection', mrp: '1850.0' },
];

export const DawaCheckScreen: React.FC = () => {
  const navigation = useNavigation<NavigationProp>();
  const { colors, spacing, typography } = useTheme();
  const { t } = useLanguage();

  // Search state
  const [brandName, setBrandName] = useState('Paracetamol 650mg');
  const [mrp, setMrp] = useState('3.5');

  // Result state
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DawaCheckBenchmarkResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleBenchmark = async (targetBrand?: string, targetMrp?: string) => {
    const brandToQuery = (targetBrand ?? brandName).trim();
    const mrpVal = parseFloat(targetMrp ?? mrp);

    if (!brandToQuery) {
      setError('Please enter a medicine or brand name.');
      return;
    }
    if (isNaN(mrpVal) || mrpVal <= 0) {
      setError('Please enter a valid MRP per unit greater than 0.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.dawacheck.benchmark({
        brand_name: brandToQuery,
        mrp: mrpVal,
      });
      setResult(response);
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.message || 'Failed to check medicine pricing.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSample = (sample: QuickSample) => {
    setBrandName(sample.name);
    setMrp(sample.mrp);
    handleBenchmark(sample.name, sample.mrp);
  };

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.bgBase }]}
      contentContainerStyle={[styles.content, { padding: spacing.md }]}
    >
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.textPrimary, fontSize: typography.sizes.xl }]}>
          💊 {t.modules.dawacheck.title}
        </Text>
        <Badge label="DPCO 2013 / NPPA" variant="warning" />
      </View>

      <Text style={[styles.desc, { color: colors.textSecondary, fontSize: typography.sizes.sm, marginBottom: spacing.md }]}>
        {t.modules.dawacheck.desc}
      </Text>

      {/* Pricing Audit Form */}
      <Card style={{ marginBottom: spacing.md }}>
        <Text style={[styles.cardTitle, { color: colors.textPrimary, marginBottom: spacing.sm }]}>
          NPPA Schedule-I Ceiling Rate Check
        </Text>

        <Text style={[styles.fieldLabel, { color: colors.textSecondary, marginBottom: 4 }]}>
          Brand / Generic Formulation Name
        </Text>
        <TextInput
          style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
          placeholder="e.g. Paracetamol 650mg, Augmentin 625"
          placeholderTextColor={colors.textMuted}
          value={brandName}
          onChangeText={setBrandName}
        />

        <Text style={[styles.fieldLabel, { color: colors.textSecondary, marginBottom: 4 }]}>
          Charged MRP / Unit Price (₹)
        </Text>
        <TextInput
          style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
          placeholder="e.g. 3.50"
          placeholderTextColor={colors.textMuted}
          keyboardType="numeric"
          value={mrp}
          onChangeText={setMrp}
        />

        {/* Quick Test Samples */}
        <Text style={[styles.fieldLabel, { color: colors.textMuted, marginTop: 4, marginBottom: 6 }]}>
          Quick verification samples:
        </Text>
        <View style={styles.samplesContainer}>
          {QUICK_SAMPLES.map((sample, idx) => (
            <TouchableOpacity
              key={idx}
              onPress={() => handleSelectSample(sample)}
              style={[styles.sampleChip, { borderColor: colors.borderSubtle, backgroundColor: 'rgba(255,255,255,0.04)' }]}
            >
              <Text style={{ color: colors.brandCyan, fontSize: 11, fontWeight: '600' }}>
                {sample.name.split(' ')[0]} (₹{sample.mrp})
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {error && (
          <Text style={{ color: '#ef4444', fontSize: 13, marginVertical: 8 }}>
            ⚠️ {error}
          </Text>
        )}

        <View style={{ marginTop: spacing.sm }}>
          <Button
            title={loading ? 'Checking NPPA Ceiling...' : '🔍 Check Price Compliance'}
            onPress={() => handleBenchmark()}
            variant="primary"
            disabled={loading}
          />
        </View>

        <View style={{ marginTop: spacing.sm }}>
          <Button
            title="📷 Scan Medicine Packaging / Strip"
            onPress={() => navigation.navigate('CameraScan', { documentType: 'prescription' })}
            variant="outline"
          />
        </View>
      </Card>

      {/* Benchmark Results */}
      {result && (
        <Card style={{ marginBottom: spacing.md }}>
          <View style={[styles.row, { marginBottom: spacing.sm }]}>
            <View style={{ flex: 1 }}>
              <Text style={{ color: colors.textPrimary, fontWeight: '700', fontSize: typography.sizes.md }}>
                {result.brand_name}
              </Text>
              <Text style={{ color: colors.textSecondary, fontSize: 12 }}>
                Active API: {result.active_ingredient}
              </Text>
            </View>
            <Badge
              label={result.is_overcharged ? `⚠️ Overcharged (+${result.deviation_percentage}%)` : '✓ Fair Price'}
              variant={result.is_overcharged ? 'danger' : 'success'}
            />
          </View>

          <View style={styles.statsRow}>
            <View style={styles.statItem}>
              <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>Charged MRP</Text>
              <Text style={{ color: colors.textPrimary, fontSize: typography.sizes.md, fontWeight: '700' }}>
                ₹{result.mrp.toFixed(2)}
              </Text>
            </View>
            <View style={styles.statItem}>
              <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>NPPA Ceiling Cap</Text>
              <Text style={{ color: colors.brandCyan, fontSize: typography.sizes.md, fontWeight: '700' }}>
                ₹{result.nppa_ceiling_price.toFixed(2)}
              </Text>
            </View>
            <View style={styles.statItem}>
              <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>Deviation</Text>
              <Text style={{ color: result.is_overcharged ? '#ef4444' : '#22c55e', fontSize: typography.sizes.md, fontWeight: '700' }}>
                {result.deviation_percentage > 0 ? `+${result.deviation_percentage}%` : '0%'}
              </Text>
            </View>
          </View>

          {/* Generic Substitute Notice */}
          {result.generic_substitute_available && (
            <View style={[styles.genericCard, { borderColor: '#22c55e' }]}>
              <Text style={{ color: '#22c55e', fontWeight: '700', fontSize: 13, marginBottom: 4 }}>
                💊 Low-Cost Generic Substitute Available
              </Text>
              <Text style={{ color: colors.textPrimary, fontSize: 12, lineHeight: 18 }}>
                {result.generic_substitute_store_info}
              </Text>
            </View>
          )}
        </Card>
      )}

      {/* Statutory DPCO 2013 Provision Notice */}
      <View style={[styles.advisoryCard, { backgroundColor: 'rgba(6, 182, 212, 0.08)', borderColor: 'rgba(6, 182, 212, 0.2)' }]}>
        <Text style={{ color: colors.brandCyan, fontWeight: '700', fontSize: 12, marginBottom: 4 }}>
          💡 Statutory Consumer Right (DPCO 2013)
        </Text>
        <Text style={{ color: colors.textSecondary, fontSize: 11, lineHeight: 17 }}>
          Under the Drugs (Prices Control) Order, 2013 and the Essential Commodities Act, 1955, charging above the notified NPPA ceiling price is an illegal punishable offence. Retail pharmacies are statutorily required to dispense equivalent generic formulations upon request.
        </Text>
      </View>
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
  fieldLabel: { fontSize: 12, fontWeight: '500' },
  input: { borderWidth: 1, borderRadius: 8, padding: 10, fontSize: 14, marginBottom: 10 },
  samplesContainer: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 8 },
  sampleChip: { borderWidth: 1, borderRadius: 16, paddingHorizontal: 10, paddingVertical: 4 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  statsRow: { flexDirection: 'row', justifyContent: 'space-between', marginVertical: 12, paddingVertical: 8, borderTopWidth: 1, borderBottomWidth: 1, borderColor: 'rgba(255,255,255,0.06)' },
  statItem: { alignItems: 'center', flex: 1 },
  genericCard: { borderLeftWidth: 3, padding: 10, borderRadius: 6, backgroundColor: 'rgba(34, 197, 94, 0.08)', marginTop: 8 },
  advisoryCard: { borderWidth: 1, borderRadius: 8, padding: 12, marginTop: 8 },
});
