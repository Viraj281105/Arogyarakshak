import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { BottomTabParamList, RootStackParamList } from '../navigation/types';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { Card, Button, Badge, TranscriptionCard, ProcessingStatusCard, CaseMedicinesCard } from '../components';
import { api, DawaCheckBenchmarkResponse, PrescriptionTranslationResponse, ApiError } from '../api';
import { useOfflineQueue } from '../hooks/useOfflineQueue';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { useCaseProcessing } from '../hooks/useCaseProcessing';
import { useActiveCaseId } from '../hooks/useActiveCase';
import { resolveCaseId } from '../services/activeCase';
import { createRequestGuard } from '../services/caseProcessing';
import { BASIS_OPTIONS, PriceBasis, buildBenchmarkRequest, describePriceCheck } from '../services/priceCheck';

type NavigationProp = NativeStackNavigationProp<RootStackParamList>;

interface QuickSample {
  name: string;
  mrp: string;
  basis: PriceBasis;
  count: string;
  caption: string;
}

// Synthetic sample prices. Each states what the amount buys, so a strip price is never
// compared with a per-tablet ceiling (the old samples produced "+1356%").
const QUICK_SAMPLES: QuickSample[] = [
  { name: 'Dolo 650', mrp: '33', basis: 'PER_STRIP', count: '15', caption: '₹33 / strip of 15' },
  { name: 'Augmentin 625 Duo', mrp: '220', basis: 'PER_PACK', count: '10', caption: '₹220 / pack of 10' },
  { name: 'Metformin 500mg SR', mrp: '18', basis: 'PER_STRIP', count: '10', caption: '₹18 / strip of 10' },
  { name: 'Meropenem 1g Injection', mrp: '900', basis: 'PER_UNIT', count: '', caption: '₹900 / vial' },
];

export const DawaCheckScreen: React.FC = () => {
  const navigation = useNavigation<NavigationProp>();
  const route = useRoute<RouteProp<BottomTabParamList, 'DawaCheck'>>();
  const { colors, spacing, typography } = useTheme();
  const { t, language } = useLanguage();
  const { enqueueAction } = useOfflineQueue();
  const { isOnline } = useNetworkStatus();
  const m = t.modules.dawacheck;

  // ADR-011: a scanned prescription arrives with its case; uncertain readings of its
  // medicines go to human transcription instead of being trusted.
  const activeCaseId = useActiveCaseId();
  const caseId = resolveCaseId(route.params?.caseId, activeCaseId);
  // Navigation happens right after the upload is accepted, while OCR/extraction still
  // runs server-side; medicines are loaded only once the server reports it finished.
  const proc = useCaseProcessing(caseId);
  const processing = !proc.ready;
  const [caseMedicines, setCaseMedicines] = useState<{ id: string; name: string }[]>([]);
  const [caseRefresh, setCaseRefresh] = useState(0);
  const medicinesGuard = useRef(createRequestGuard()).current;
  useEffect(() => {
    if (!caseId || !proc.ready) {
      medicinesGuard.reset();
      setCaseMedicines([]);
      return;
    }
    const token = medicinesGuard.begin();
    api.kadi
      .getCase(caseId)
      .then((res) => {
        if (medicinesGuard.isCurrent(token)) {
          setCaseMedicines(res.entities.filter((e) => e.type === 'medicine').map((e) => ({ id: e.id, name: e.name })));
        }
      })
      .catch(() => {
        if (medicinesGuard.isCurrent(token)) setCaseMedicines([]);
      });
  }, [caseId, proc.ready, caseRefresh, medicinesGuard]);

  // Prescription shorthand translator (#97)
  const [instructionsText, setInstructionsText] = useState('');
  const [translation, setTranslation] = useState<PrescriptionTranslationResponse | null>(null);
  const [translating, setTranslating] = useState(false);

  const handleTranslate = async () => {
    if (!instructionsText.trim()) return;
    setTranslating(true);
    try {
      const res = await api.dawacheck.translateInstructions({
        instructions: instructionsText.trim(),
        language,
      });
      setTranslation(res);
    } catch {
      // Best-effort feature; translation failure should not block the rest of the screen.
    } finally {
      setTranslating(false);
    }
  };

  // Search state
  // The MRP drives an "overcharged" verdict, so it must be the price the user actually
  // paid — never a sample value they might submit unchanged.
  const [brandName, setBrandName] = useState('');
  const [mrp, setMrp] = useState('');
  const [basis, setBasis] = useState<PriceBasis | null>(null);
  const [count, setCount] = useState('');
  const basisOption = BASIS_OPTIONS.find((o) => o.value === basis);

  // Result state
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DawaCheckBenchmarkResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [offlineQueued, setOfflineQueued] = useState(false);

  const handleBenchmark = async (sample?: QuickSample) => {
    const built = sample
      ? buildBenchmarkRequest(sample.name, sample.mrp, sample.basis, sample.count)
      : buildBenchmarkRequest(brandName, mrp, basis, count);
    if (!built.ok) {
      setError(built.error);
      return;
    }

    setLoading(true);
    setError(null);
    setOfflineQueued(false);

    try {
      const response = await api.dawacheck.benchmark(built.body);
      setResult(response);
    } catch (err) {
      const apiErr = err as ApiError;
      const queuedId = await enqueueAction('BENCHMARK_MEDICINE', { ...built.body });
      if (queuedId) {
        setOfflineQueued(true);
        setError(
          !isOnline
            ? 'Device is offline. Medicine audit queued; will sync automatically when reconnected.'
            : `${apiErr.message || 'Failed to check medicine pricing.'} (Queued for offline retry)`
        );
      } else {
        setOfflineQueued(false);
        setError('Could not save this for offline retry — please try again when back online.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSample = (sample: QuickSample) => {
    setBrandName(sample.name);
    setMrp(sample.mrp);
    setBasis(sample.basis);
    setCount(sample.count);
    handleBenchmark(sample);
  };
  const price = result ? describePriceCheck(result) : null;

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.bgBase }]}
      contentContainerStyle={[styles.content, { padding: spacing.md }]}
    >
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.textPrimary, fontSize: typography.sizes.xl }]}>
          💊 {m.title}
        </Text>
        <Badge label={m.statutory} variant="warning" />
      </View>

      <Text style={[styles.desc, { color: colors.textSecondary, fontSize: typography.sizes.sm, marginBottom: spacing.md }]}>
        {m.desc}
      </Text>

      <ProcessingStatusCard proc={proc} />
      <CaseMedicinesCard caseId={caseId} ready={proc.ready} refreshToken={caseRefresh} onChanged={() => setCaseRefresh((n) => n + 1)} />

      {/* Pricing Audit Form */}
      <Card style={{ marginBottom: spacing.md }}>
        <Text style={[styles.cardTitle, { color: colors.textPrimary, marginBottom: spacing.sm }]}>
          {m.cardTitle}
        </Text>

        <Text style={[styles.fieldLabel, { color: colors.textSecondary, marginBottom: 4 }]}>
          {m.brandOrGeneric}
        </Text>
        <TextInput
          style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
          placeholder="e.g. Paracetamol 650mg, Augmentin 625"
          placeholderTextColor={colors.textMuted}
          value={brandName}
          onChangeText={setBrandName}
        />

        <Text style={[styles.fieldLabel, { color: colors.textSecondary, marginBottom: 4 }]}>
          {m.chargedMrp}
        </Text>
        <TextInput
          style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
          placeholder="Amount paid, e.g. 33"
          placeholderTextColor={colors.textMuted}
          keyboardType="numeric"
          value={mrp}
          onChangeText={setMrp}
        />

        <Text style={[styles.fieldLabel, { color: colors.textSecondary, marginBottom: 4 }]}>
          The amount paid is for… (NPPA ceilings are per tablet/capsule/vial)
        </Text>
        <View style={styles.samplesContainer}>
          {BASIS_OPTIONS.map((o) => (
            <TouchableOpacity
              key={o.value}
              accessibilityRole="radio"
              accessibilityState={{ selected: basis === o.value }}
              onPress={() => {
                setBasis(o.value);
                setCount('');
              }}
              style={[
                styles.sampleChip,
                { borderColor: basis === o.value ? colors.brandCyan : colors.borderSubtle, minHeight: 44, justifyContent: 'center' },
              ]}
            >
              <Text style={{ color: basis === o.value ? colors.brandCyan : colors.textSecondary, fontSize: 12, fontWeight: '600' }}>
                {o.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
        {basisOption && basisOption.needs !== 'none' && (
          <TextInput
            style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
            placeholder={basisOption.needs === 'pack' ? 'Units in the strip/pack, e.g. 15' : 'Number of units, e.g. 10'}
            placeholderTextColor={colors.textMuted}
            keyboardType="number-pad"
            value={count}
            onChangeText={setCount}
          />
        )}

        {/* Quick Test Samples */}
        <Text style={[styles.fieldLabel, { color: colors.textMuted, marginTop: 4, marginBottom: 6 }]}>
          {m.quickSamples}
        </Text>
        <View style={styles.samplesContainer}>
          {QUICK_SAMPLES.map((sample, idx) => (
            <TouchableOpacity
              key={idx}
              onPress={() => handleSelectSample(sample)}
              style={[styles.sampleChip, { borderColor: colors.borderSubtle, backgroundColor: 'rgba(255,255,255,0.04)' }]}
            >
              <Text style={{ color: colors.brandCyan, fontSize: 11, fontWeight: '600' }}>
                {sample.name.split(' ')[0]} · {sample.caption}
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
            title={loading ? m.checking : m.checkBtn}
            onPress={() => handleBenchmark()}
            variant="primary"
            disabled={loading}
          />
        </View>

        <View style={{ marginTop: spacing.sm }}>
          <Button
            title={m.scanStrip}
            onPress={() => navigation.navigate('CameraScan', { documentType: 'prescription' })}
            variant="outline"
          />
        </View>
      </Card>

      {/* Benchmark Results */}
      {result && price && (
        <Card style={{ marginBottom: spacing.md }}>
          <View style={[styles.row, { marginBottom: spacing.sm }]}>
            <View style={{ flex: 1 }}>
              <Text style={{ color: colors.textPrimary, fontWeight: '700', fontSize: typography.sizes.md }}>
                {result.brand_name}
              </Text>
              <Text style={{ color: colors.textSecondary, fontSize: 12 }}>
                {m.activeApi} {result.active_ingredient}
              </Text>
            </View>
            <Badge label={price.badge} variant={price.variant} />
          </View>

          <View style={{ marginVertical: 8, gap: 4 }}>
            <Text style={{ color: colors.textPrimary, fontSize: typography.sizes.sm, fontWeight: '600' }}>{price.billed}</Text>
            <Text style={{ color: colors.brandCyan, fontSize: typography.sizes.sm, fontWeight: '600' }}>{price.ceiling}</Text>
            {price.reason && <Text style={{ color: colors.statusWarning, fontSize: typography.sizes.xs }}>{price.reason}</Text>}
            {price.basisNote && <Text style={{ color: colors.textMuted, fontSize: typography.sizes.xs }}>{price.basisNote}</Text>}
          </View>

          {/* Generic Substitute Notice */}
          {result.generic_substitute_available && (
            <View style={[styles.genericCard, { borderColor: '#22c55e' }]}>
              <Text style={{ color: '#22c55e', fontWeight: '700', fontSize: 13, marginBottom: 4 }}>
                {m.genericAvailable}
              </Text>
              <Text style={{ color: colors.textPrimary, fontSize: 12, lineHeight: 18 }}>
                {result.generic_substitute_store_info}
              </Text>
            </View>
          )}

          {/* Dataset Provenance Disclosure */}
          <Text style={{ color: '#f59e0b', fontSize: 11, lineHeight: 16, marginTop: 10 }}>
            ⓘ {m.dataSourceNotice.replace('{count}', String(result.reference_entry_count))}
          </Text>
        </Card>
      )}

      {/* Prescription Shorthand Translator (#97) */}
      <Card style={{ marginBottom: spacing.md }}>
        <Text style={[styles.cardTitle, { color: colors.textPrimary, marginBottom: spacing.sm }]}>
          {m.prescriptionTranslatorTitle}
        </Text>
        <TextInput
          style={[styles.input, { color: colors.textPrimary, borderColor: colors.borderSubtle }]}
          placeholder={m.prescriptionInputPlaceholder}
          placeholderTextColor={colors.textMuted}
          value={instructionsText}
          onChangeText={setInstructionsText}
          multiline
        />
        <Button
          title={m.translateBtn}
          onPress={handleTranslate}
          variant="secondary"
          disabled={translating || !instructionsText.trim()}
        />
        {translation && translation.instructions.length > 0 && (
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: spacing.sm }}>
            {translation.instructions.map((instr, idx) => (
              <Badge
                key={idx}
                label={instr.recognized ? `${instr.token} → ${instr.translated}` : `${instr.token} ?`}
                variant={instr.recognized ? 'success' : 'danger'}
              />
            ))}
          </View>
        )}
        {translation && translation.unrecognized_tokens.length > 0 && (
          <Text style={{ color: '#f59e0b', fontSize: 11, lineHeight: 16, marginTop: spacing.xs }}>
            ⓘ {m.unrecognizedNotice.replace('{tokens}', translation.unrecognized_tokens.join(', '))}
          </Text>
        )}
      </Card>

      {/* Statutory DPCO 2013 Provision Notice */}
      <View style={[styles.advisoryCard, { backgroundColor: 'rgba(6, 182, 212, 0.08)', borderColor: 'rgba(6, 182, 212, 0.2)' }]}>
        <Text style={{ color: colors.brandCyan, fontWeight: '700', fontSize: 12, marginBottom: 4 }}>
          {m.statutoryNoticeTitle}
        </Text>
        <Text style={{ color: colors.textSecondary, fontSize: 11, lineHeight: 17 }}>
          {m.statutoryNoticeBody}
        </Text>
      </View>
      <TranscriptionCard caseId={caseId} medicines={caseMedicines} processing={processing} refreshToken={`${proc.ready}-${caseRefresh}`} />
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
