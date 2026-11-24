/**
 * DEV ONLY: every Wave 3 M2 primitive in both themes. App.tsx loads this file only behind
 * `__DEV__` (a `require` inside a `__DEV__` conditional, which Metro removes from production
 * bundles); open it in the web preview with `?gallery` or from the native dev menu
 * ("Primitives gallery"). Not a product screen: copy here is sample text, not real data.
 */
import React, { useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { ThemeProvider, useTheme, textStyles, type ThemeMode } from '../theme';
import { Button } from '../components/Button';
import { Badge } from '../components/Badge';
import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { SkeletonCard } from '../components/Skeleton';
import {
  BottomSheet,
  Checklist,
  ConfidenceIndicator,
  ConfirmationDialog,
  CITATION_TO_EVIDENCE,
  EVIDENCE_STATES,
  ErrorState,
  EvidenceBadge,
  Icon,
  InsufficientEvidenceState,
  LoadingState,
  MetricCard,
  OfflineState,
  PartialResultState,
  StatusBadge,
  StepWizard,
  ToastProvider,
  useToast,
} from '../components/ui';
import { BUTTON_VARIANTS, BADGE_VARIANTS, STATUS_TONES, TOAST_TONES } from '../components/ui/tones';
import { ACTION_GLYPHS, MODULE_GLYPHS, type ActionIcon, type IconModule } from '../icons/glyphs';
import { Pressable } from '../motion';

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  const { colors, spacing } = useTheme();
  return (
    <View style={{ marginTop: spacing.lg }}>
      <Text accessibilityRole="header" style={[textStyles.title, { color: colors.textPrimary, marginBottom: spacing.sm }]}>
        {title}
      </Text>
      {children}
    </View>
  );
}

const Row = ({ children }: { children: React.ReactNode }) => <View style={styles.row}>{children}</View>;

function Gallery({ mode, setMode, onExit }: { mode: ThemeMode; setMode: (m: ThemeMode) => void; onExit?: () => void }) {
  const { colors, spacing, radii } = useTheme();
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const [sheet, setSheet] = useState(false);
  const [confirm, setConfirm] = useState<null | 'plain' | 'destructive'>(null);
  const [result, setResult] = useState('none yet');
  const [step, setStep] = useState(1);

  return (
    <View style={{ flex: 1, backgroundColor: colors.bgBase }}>
      <ScrollView
        contentContainerStyle={{
          paddingTop: insets.top + spacing.md,
          paddingBottom: insets.bottom + 120,
          paddingHorizontal: spacing.md,
        }}
      >
        <Text accessibilityRole="header" style={[textStyles.brand, { color: colors.textPrimary }]}>
          Primitives (dev only)
        </Text>
        <Text style={[textStyles.bodySmall, { color: colors.textSecondary }]}>
          Wave 3 M2 mobile foundation. Sample content only.
        </Text>
        <View accessibilityRole="radiogroup" style={[styles.row, { marginTop: spacing.sm }]}>
          {(['dark', 'light'] as const).map((m) => (
            <Pressable
              key={m}
              onPress={() => setMode(m)}
              accessibilityRole="radio"
              accessibilityState={{ checked: mode === m, selected: mode === m }}
              aria-checked={mode === m}
              accessibilityLabel={`${m} theme`}
              style={[
                styles.chip,
                {
                  minHeight: spacing.minTouchTarget,
                  borderRadius: radii.md,
                  borderColor: colors.borderMedium,
                  backgroundColor: mode === m ? colors.actionPrimary : colors.bgSurface,
                },
              ]}
            >
              <Text style={[textStyles.labelSmall, { color: mode === m ? colors.textOnAction : colors.textSecondary }]}>
                {m === 'dark' ? 'Dark' : 'Light'}
              </Text>
            </Pressable>
          ))}
          {onExit ? <Button title="Back to app" variant="ghost" size="sm" onPress={onExit} /> : null}
        </View>

        <Section title="Button">
          <Row>
            {BUTTON_VARIANTS.map((v) => (
              <Button key={v} title={v[0].toUpperCase() + v.slice(1)} variant={v} onPress={() => setResult(`pressed ${v}`)} />
            ))}
            <Button title="Disabled" disabled onPress={() => undefined} />
            <Button title="Loading" loading onPress={() => undefined} />
          </Row>
          <Text style={[textStyles.caption, { color: colors.textMuted }]}>Last action: {result}</Text>
        </Section>

        <Section title="EvidenceBadge (eight states)">
          {EVIDENCE_STATES.map((s) => (
            <EvidenceBadge key={s} state={s} showMeaning style={{ marginBottom: spacing.sm }} />
          ))}
          <Text style={[textStyles.labelSmall, { color: colors.textSecondary, marginTop: spacing.sm }]}>
            Wave 2 citation status → evidence state
          </Text>
          {Object.entries(CITATION_TO_EVIDENCE).map(([c, e]) => (
            <View key={c} style={[styles.row, { alignItems: 'center' }]}>
              <Text style={[textStyles.mono, { color: colors.textSecondary }]}>{c} →</Text>
              <EvidenceBadge state={e} size="sm" />
            </View>
          ))}
          <View style={[styles.row, { alignItems: 'center' }]}>
            <Text style={[textStyles.mono, { color: colors.textSecondary }]}>anything else →</Text>
            <EvidenceBadge state="unevaluated" size="sm" />
          </View>
        </Section>

        <Section title="StatusBadge and legacy Badge">
          <Row>
            {STATUS_TONES.map((t) => (
              <StatusBadge key={t} tone={t} label={t === 'neutral' ? 'Not started' : t[0].toUpperCase() + t.slice(1)} />
            ))}
          </Row>
          <Row>
            {BADGE_VARIANTS.map((v) => (
              <Badge key={v} label={v} variant={v} />
            ))}
          </Row>
        </Section>

        <Section title="ConfidenceIndicator">
          <Card reveal={false}>
            <ConfidenceIndicator value={0.93} source="OCR engine" label="Extraction confidence" />
            <ConfidenceIndicator value={0.71} source="OCR engine" style={{ marginTop: spacing.sm }} />
            <ConfidenceIndicator value={0.32} source="Entity matcher" style={{ marginTop: spacing.sm }} />
          </Card>
        </Section>

        <Section title="MetricCard">
          <MetricCard label="Possible overcharge" value="₹12,450" basis="estimate" source="BillNyay vs CGHS 2024 rates" period="This bill" />
          <MetricCard
            label="NPPA ceiling price"
            value="₹2.37"
            unit="per tablet"
            basis="verified"
            source="NPPA Schedule-I"
            note="Sample figure for the gallery."
          />
        </Section>

        <Section title="StepWizard header">
          <Card reveal={false}>
            <StepWizard
              current={step}
              steps={[
                { id: 'ready', label: 'Readiness' },
                { id: 'form', label: 'Template' },
                { id: 'pkg', label: 'Package' },
              ]}
            >
              <Row>
                <Button title="Back" variant="secondary" size="sm" disabled={step === 0} onPress={() => setStep((s) => Math.max(0, s - 1))} />
                <Button title="Next" size="sm" disabled={step === 3} onPress={() => setStep((s) => Math.min(3, s + 1))} />
              </Row>
            </StepWizard>
          </Card>
        </Section>

        <Section title="Checklist">
          <Card reveal={false}>
            <Checklist
              title="Pre-authorisation readiness"
              items={[
                { id: 'id', label: 'Patient ID document', status: 'done' },
                { id: 'policy', label: 'Policy number', status: 'todo', note: 'Printed on the insurance card' },
                { id: 'diag', label: 'Diagnosis from the doctor', status: 'blocked', note: 'Needs the doctor’s note' },
                { id: 'est', label: 'Cost estimate', status: 'unknown' },
              ]}
            />
          </Card>
        </Section>

        <Section title="States">
          <LoadingState label="Reading your bill…" lines={2} />
          <EmptyState title="No cases yet" body="Scan or upload a bill to start a case." actionLabel="Scan a bill" onAction={() => setResult('empty action')} />
          <ErrorState
            title="Could not reach the server"
            body="The upload did not finish."
            action={<Button title="Try again" variant="secondary" size="sm" onPress={() => setResult('retry')} />}
          />
          <PartialResultState missing={['Room charges (unreadable line)', 'Pharmacy page 3']} body="Two of five pages were read." />
          <InsufficientEvidenceState reason="No CGHS row matches this line item." />
          <OfflineState action={<Button title="Retry" variant="secondary" size="sm" onPress={() => setResult('offline retry')} />} />
          <SkeletonCard />
        </Section>

        <Section title="Toast">
          <Row>
            {TOAST_TONES.map((t) => (
              <Button
                key={t}
                title={`Show ${t}`}
                variant="secondary"
                size="sm"
                onPress={() => toast({ tone: t, message: t === 'error' ? 'Upload failed. Nothing was saved.' : `Sample ${t} message.` })}
              />
            ))}
          </Row>
        </Section>

        <Section title="BottomSheet and ConfirmationDialog">
          <Row>
            <Button title="Open sheet" variant="secondary" onPress={() => setSheet(true)} />
            <Button title="Confirm" variant="secondary" onPress={() => setConfirm('plain')} />
            <Button title="Delete case" variant="danger" onPress={() => setConfirm('destructive')} />
          </Row>
        </Section>

        <Section title="Icon map (glyphs)">
          <Text style={[textStyles.caption, { color: colors.textMuted, marginBottom: spacing.xs }]}>
            Modules (emoji, not tintable)
          </Text>
          <Row>
            {(Object.keys(MODULE_GLYPHS) as IconModule[]).map((m) => (
              <View key={m} style={styles.iconCell}>
                <Icon name={{ module: m }} size={22} />
                <Text style={[textStyles.caption, { color: colors.textSecondary }]}>{m}</Text>
              </View>
            ))}
          </Row>
          <Text style={[textStyles.caption, { color: colors.textMuted, marginVertical: spacing.xs }]}>Actions</Text>
          <Row>
            {(Object.keys(ACTION_GLYPHS) as ActionIcon[]).map((a) => (
              <View key={a} style={styles.iconCell}>
                <Icon name={{ action: a }} size={20} color={colors.textPrimary} />
                <Text style={[textStyles.caption, { color: colors.textSecondary }]}>{a}</Text>
              </View>
            ))}
          </Row>
        </Section>
      </ScrollView>

      <BottomSheet open={sheet} onClose={() => setSheet(false)} title="Why this line was flagged">
        <EvidenceBadge state="rule-engine" />
        <Text style={[textStyles.body, { color: colors.textSecondary, marginTop: spacing.sm }]}>
          Sample sheet content. Close with the button, a tap outside, or the Android back button.
        </Text>
        <Button title="Done" onPress={() => setSheet(false)} style={{ marginTop: spacing.md }} />
      </BottomSheet>
      <ConfirmationDialog
        open={confirm !== null}
        destructive={confirm === 'destructive'}
        title={confirm === 'destructive' ? 'Delete this case?' : 'Send the appeal draft?'}
        consequence={
          confirm === 'destructive'
            ? 'The case and its extracted data are removed from this phone. This cannot be undone.'
            : 'Sample confirmation. Nothing is sent from the gallery.'
        }
        confirmLabel={confirm === 'destructive' ? 'Delete case' : 'Send draft'}
        onCancel={() => {
          setConfirm(null);
          setResult('cancelled');
        }}
        onConfirm={() => {
          setConfirm(null);
          setResult('confirmed');
        }}
      />
    </View>
  );
}

export function PrimitivesGallery({ onExit }: { onExit?: () => void }) {
  const { mode: appMode } = useTheme();
  const [mode, setMode] = useState<ThemeMode>(appMode);
  return (
    <ThemeProvider forcedMode={mode}>
      <ToastProvider>
        <Gallery mode={mode} setMode={setMode} onExit={onExit} />
      </ToastProvider>
    </ThemeProvider>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 8 },
  chip: { paddingHorizontal: 16, alignItems: 'center', justifyContent: 'center', borderWidth: 1 },
  iconCell: { width: 72, alignItems: 'center', paddingVertical: 4 },
});
