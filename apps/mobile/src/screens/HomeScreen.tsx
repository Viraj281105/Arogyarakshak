import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { Card, Button, Badge } from '../components';

type NavigationProp = NativeStackNavigationProp<RootStackParamList>;

export const HomeScreen: React.FC = () => {
  const navigation = useNavigation<NavigationProp>();
  const { colors, spacing, typography, radii, isDark } = useTheme();
  const { t } = useLanguage();

  const openScanner = (type: 'bill' | 'prescription' | 'denial' | 'general' = 'general') => {
    navigation.navigate('CameraScan', { documentType: type });
  };

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.bgBase }]}
      contentContainerStyle={[styles.content, { padding: spacing.md }]}
    >
      {/* Compact Sovereign Brand Header */}
      <View style={[styles.hero, { marginBottom: spacing.md }]}>
        <View style={styles.brandRow}>
          <View style={[styles.emblemBadge, { backgroundColor: colors.bgSurfaceElevated, borderColor: colors.borderMedium }]}>
            <Text style={{ fontSize: 18 }}>🛡️</Text>
          </View>
          <View>
            <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 6 }}>
              <Text
                style={[
                  styles.heroTitle,
                  {
                    color: colors.textPrimary,
                    fontSize: typography.sizes.xl,
                    fontWeight: typography.weights.extrabold,
                  },
                ]}
              >
                {t.appName}
              </Text>
              <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.sm }}>| आरोग्यरक्षक</Text>
            </View>
            <Text
              style={{
                color: colors.textMuted,
                fontSize: 10,
                textTransform: 'uppercase',
                letterSpacing: 0.5,
                fontWeight: typography.weights.semibold,
              }}
            >
              Sovereign Health Intelligence • DPDP Act 2023
            </Text>
          </View>
        </View>
        <Text
          style={[
            styles.heroTagline,
            {
              color: colors.textSecondary,
              fontSize: typography.sizes.sm,
              lineHeight: typography.lineHeights.sm,
              marginTop: spacing.sm,
            },
          ]}
        >
          {t.tagline}
        </Text>
      </View>

      {/* DPDP Enclave Security Chip */}
      <Card style={{ marginBottom: spacing.md, backgroundColor: isDark ? 'rgba(16, 185, 129, 0.08)' : 'rgba(16, 185, 129, 0.05)', borderColor: 'rgba(16, 185, 129, 0.25)' }}>
        <View style={styles.byodHeader}>
          <Badge label={t.byodBadge} variant="success" />
        </View>
        <Text
          style={[
            styles.byodText,
            {
              color: colors.textSecondary,
              fontSize: typography.sizes.xs,
              lineHeight: typography.lineHeights.xs,
              marginTop: spacing.xs,
            },
          ]}
        >
          {t.byodDescription}
        </Text>
      </Card>

      {/* Hero Quick Camera Scanner Card */}
      <Card
        elevated
        style={{
          marginBottom: spacing.lg,
          backgroundColor: colors.bgSurface,
          borderColor: colors.borderMedium,
          padding: spacing.md,
        }}
      >
        <View style={styles.scannerHeroContent}>
          <View
            style={[
              styles.scannerReticle,
              {
                backgroundColor: colors.bgSurfaceElevated,
                borderColor: colors.borderMedium,
              },
            ]}
          >
            <Text style={{ fontSize: 30 }}>📷</Text>
          </View>
          <Text
            style={{
              color: colors.textPrimary,
              fontSize: typography.sizes.md,
              fontWeight: typography.weights.bold,
              textAlign: 'center',
              marginTop: spacing.xs,
            }}
          >
            Scan Hospital Bill or Claim Letter
          </Text>
          <Text
            style={{
              color: colors.textSecondary,
              fontSize: typography.sizes.xs,
              textAlign: 'center',
              lineHeight: 18,
              marginTop: 4,
              marginBottom: spacing.md,
            }}
          >
            Instant Zero-Retention OCR Audit against CGHS 2024 tariffs &amp; NPPA price caps
          </Text>

          <Button
            title={`📷  ${t.scanner.capture}`}
            onPress={() => openScanner('general')}
            variant="primary"
            size="lg"
            style={{ width: '100%' }}
          />
        </View>
      </Card>

      {/* Active Recovery Case Dossier Preview */}
      <Card
        style={{
          marginBottom: spacing.lg,
          backgroundColor: colors.bgSurface,
          borderColor: colors.statusDanger,
          borderLeftWidth: 4,
          borderLeftColor: colors.statusDanger,
        }}
      >
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.xs }}>
          <Text style={{ color: colors.textPrimary, fontSize: typography.sizes.sm, fontWeight: typography.weights.bold }}>
            Active Dossier: Rameshwar Shinde
          </Text>
          <Badge label="3 FLAGS" variant="danger" />
        </View>
        <Text style={{ color: colors.textMuted, fontSize: typography.sizes.xs, marginBottom: spacing.xs }}>
          PTCA Stenting • Metro Heart Super Speciality
        </Text>
        <View style={{ flexDirection: 'row', gap: 8, marginTop: 4, marginBottom: spacing.sm, flexWrap: 'wrap' }}>
          <View style={[styles.metricPill, { backgroundColor: isDark ? 'rgba(224, 122, 95, 0.16)' : 'rgba(184, 93, 67, 0.12)' }]}>
            <Text style={{ color: colors.statusDanger, fontSize: 11, fontWeight: '700' }}>₹1,88,350 Disallowed</Text>
          </View>
          <View style={[styles.metricPill, { backgroundColor: isDark ? 'rgba(229, 168, 75, 0.16)' : 'rgba(196, 125, 43, 0.12)' }]}>
            <Text style={{ color: colors.statusWarning, fontSize: 11, fontWeight: '700' }}>Stent Cap Breach</Text>
          </View>
        </View>
        <Button
          title="Inspect Bill Audit Findings →"
          onPress={() => (navigation as any).navigate('MainTabs', { screen: 'BillNyay' })}
          variant="secondary"
          size="sm"
          style={{ width: '100%' }}
        />
      </Card>

      {/* 4-Stage Forensic Intelligence Narrative Summary */}
      <Card
        style={{
          marginBottom: spacing.lg,
          backgroundColor: colors.bgSurface,
          borderColor: colors.borderSubtle,
        }}
      >
        <Text
          style={{
            color: colors.brandEmerald,
            fontSize: 10,
            fontFamily: 'monospace',
            fontWeight: '700',
            textTransform: 'uppercase',
            letterSpacing: 0.5,
            marginBottom: spacing.xs,
          }}
        >
          Forensic Adjudication Lifecycle
        </Text>
        <Text
          style={{
            color: colors.textPrimary,
            fontSize: typography.sizes.sm,
            fontWeight: typography.weights.bold,
            marginBottom: spacing.sm,
          }}
        >
          From Raw Medical Invoices to Sovereign Rights
        </Text>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 4, marginBottom: spacing.sm }}>
          <View style={[styles.lifecycleStep, { backgroundColor: isDark ? 'rgba(224, 122, 95, 0.14)' : 'rgba(184, 93, 67, 0.1)', borderColor: colors.borderSubtle }]}>
            <Text style={{ color: colors.statusDanger, fontSize: 9, fontWeight: '700' }}>01 INTAKE</Text>
            <Text style={{ color: colors.textSecondary, fontSize: 8 }}>Raw Chaos</Text>
          </View>
          <View style={[styles.lifecycleStep, { backgroundColor: isDark ? 'rgba(112, 151, 176, 0.14)' : 'rgba(74, 107, 130, 0.1)', borderColor: colors.borderSubtle }]}>
            <Text style={{ color: colors.brandCyan, fontSize: 9, fontWeight: '700' }}>02 PARSE</Text>
            <Text style={{ color: colors.textSecondary, fontSize: 8 }}>WASM PII</Text>
          </View>
          <View style={[styles.lifecycleStep, { backgroundColor: isDark ? 'rgba(229, 168, 75, 0.14)' : 'rgba(196, 125, 43, 0.1)', borderColor: colors.borderSubtle }]}>
            <Text style={{ color: colors.statusWarning, fontSize: 9, fontWeight: '700' }}>03 AUDIT</Text>
            <Text style={{ color: colors.textSecondary, fontSize: 8 }}>CGHS Caps</Text>
          </View>
          <View style={[styles.lifecycleStep, { backgroundColor: isDark ? 'rgba(82, 183, 136, 0.14)' : 'rgba(45, 106, 79, 0.1)', borderColor: colors.borderSubtle }]}>
            <Text style={{ color: colors.brandEmerald, fontSize: 9, fontWeight: '700' }}>04 REMEDY</Text>
            <Text style={{ color: colors.textSecondary, fontSize: 8 }}>Form VI</Text>
          </View>
        </View>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, paddingTop: 6, borderTopWidth: 1, borderTopColor: colors.borderSubtle }}>
          <Text style={{ color: colors.textMuted, fontSize: 9 }}>✓ Sec 45 Incontestable</Text>
          <Text style={{ color: colors.textMuted, fontSize: 9 }}>•</Text>
          <Text style={{ color: colors.textMuted, fontSize: 9 }}>✓ IRDAI 60-Min SLA</Text>
          <Text style={{ color: colors.textMuted, fontSize: 9 }}>•</Text>
          <Text style={{ color: colors.textMuted, fontSize: 9 }}>✓ NPPA S.O. 1335(E)</Text>
        </View>
      </Card>

      {/* Module Navigation Overview */}
      <Text
        style={[
          styles.sectionHeading,
          {
            color: colors.textPrimary,
            fontSize: typography.sizes.md,
            fontWeight: typography.weights.bold,
            marginBottom: spacing.sm,
          },
        ]}
      >
        ArogyaRakshak Modules
      </Text>

      {/* 1. BillNyay */}
      <TouchableOpacity
        activeOpacity={0.8}
        onPress={() => (navigation as any).navigate('MainTabs', { screen: 'BillNyay' })}
      >
        <Card style={styles.moduleCard}>
          <View style={styles.moduleHeader}>
            <Text style={[styles.moduleTitle, { color: colors.textPrimary, fontSize: typography.sizes.md }]}>
              ⚖️ {t.modules.billnyay.title}
            </Text>
            <Badge label="CGHS 2024" variant="info" />
          </View>
          <Text style={[styles.moduleDesc, { color: colors.textSecondary, fontSize: typography.sizes.sm }]}>
            {t.modules.billnyay.desc}
          </Text>
        </Card>
      </TouchableOpacity>

      {/* 2. DaaviSetu */}
      <TouchableOpacity
        activeOpacity={0.8}
        onPress={() => (navigation as any).navigate('MainTabs', { screen: 'DaaviSetu' })}
      >
        <Card style={styles.moduleCard}>
          <View style={styles.moduleHeader}>
            <Text style={[styles.moduleTitle, { color: colors.textPrimary, fontSize: typography.sizes.md }]}>
              📋 {t.modules.daavisetu.title}
            </Text>
            <Badge label="Pre-Auth" variant="brand" />
          </View>
          <Text style={[styles.moduleDesc, { color: colors.textSecondary, fontSize: typography.sizes.sm }]}>
            {t.modules.daavisetu.desc}
          </Text>
        </Card>
      </TouchableOpacity>

      {/* 3. BimaNyay */}
      <TouchableOpacity
        activeOpacity={0.8}
        onPress={() => (navigation as any).navigate('MainTabs', { screen: 'BimaNyay' })}
      >
        <Card style={styles.moduleCard}>
          <View style={styles.moduleHeader}>
            <Text style={[styles.moduleTitle, { color: colors.textPrimary, fontSize: typography.sizes.md }]}>
              🛡️ {t.modules.bimanyay.title}
            </Text>
            <Badge label="IRDAI 2024" variant="danger" />
          </View>
          <Text style={[styles.moduleDesc, { color: colors.textSecondary, fontSize: typography.sizes.sm }]}>
            {t.modules.bimanyay.desc}
          </Text>
        </Card>
      </TouchableOpacity>

      {/* 4. SchemeSetu */}
      <TouchableOpacity
        activeOpacity={0.8}
        onPress={() => (navigation as any).navigate('MainTabs', { screen: 'SchemeSetu' })}
      >
        <Card style={styles.moduleCard}>
          <View style={styles.moduleHeader}>
            <Text style={[styles.moduleTitle, { color: colors.textPrimary, fontSize: typography.sizes.md }]}>
              🏛️ {t.modules.schemesetu.title}
            </Text>
            <Badge label="PMJAY / MJPJAY" variant="success" />
          </View>
          <Text style={[styles.moduleDesc, { color: colors.textSecondary, fontSize: typography.sizes.sm }]}>
            {t.modules.schemesetu.desc}
          </Text>
        </Card>
      </TouchableOpacity>

      {/* 5. DawaCheck */}
      <TouchableOpacity
        activeOpacity={0.8}
        onPress={() => (navigation as any).navigate('MainTabs', { screen: 'DawaCheck' })}
      >
        <Card style={styles.moduleCard}>
          <View style={styles.moduleHeader}>
            <Text style={[styles.moduleTitle, { color: colors.textPrimary, fontSize: typography.sizes.md }]}>
              💊 {t.modules.dawacheck.title}
            </Text>
            <Badge label="NPPA Ceiling" variant="warning" />
          </View>
          <Text style={[styles.moduleDesc, { color: colors.textSecondary, fontSize: typography.sizes.sm }]}>
            {t.modules.dawacheck.desc}
          </Text>
        </Card>
      </TouchableOpacity>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    paddingBottom: 40,
  },
  hero: {
    alignItems: 'flex-start',
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  emblemBadge: {
    width: 40,
    height: 40,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroTitle: {
    letterSpacing: -0.5,
  },
  heroTagline: {
    marginTop: 4,
  },
  byodHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  byodText: {
    marginTop: 4,
  },
  scannerHeroContent: {
    alignItems: 'center',
  },
  scannerReticle: {
    width: 60,
    height: 60,
    borderRadius: 30,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  metricPill: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  sectionHeading: {
    letterSpacing: -0.2,
  },
  moduleCard: {
    marginVertical: 4,
  },
  moduleHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  moduleTitle: {
    fontWeight: '700',
  },
  moduleDesc: {
    lineHeight: 20,
  },
  lifecycleStep: {
    flex: 1,
    paddingVertical: 6,
    paddingHorizontal: 4,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
  },
});
