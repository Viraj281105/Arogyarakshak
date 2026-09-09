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
  const { colors, spacing, typography, radii } = useTheme();
  const { t } = useLanguage();

  const openScanner = (type: 'bill' | 'prescription' | 'denial' | 'general' = 'general') => {
    navigation.navigate('CameraScan', { documentType: type });
  };

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.bgBase }]}
      contentContainerStyle={[styles.content, { padding: spacing.md }]}
    >
      {/* Hero Branding Section */}
      <View style={[styles.hero, { marginBottom: spacing.md }]}>
        <Text
          style={[
            styles.heroTitle,
            {
              color: colors.textPrimary,
              fontSize: typography.sizes.xxl,
              fontWeight: typography.weights.bold,
            },
          ]}
        >
          {t.appName}
        </Text>
        <Text
          style={[
            styles.heroTagline,
            {
              color: colors.textSecondary,
              fontSize: typography.sizes.sm,
              lineHeight: typography.lineHeights.sm,
              marginTop: spacing.xs,
            },
          ]}
        >
          {t.tagline}
        </Text>
      </View>

      {/* BYOD Privacy Assurance Banner */}
      <Card style={{ marginBottom: spacing.md, backgroundColor: 'rgba(6, 182, 212, 0.08)' }}>
        <View style={styles.byodHeader}>
          <Badge label={t.byodBadge} variant="brand" />
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

      {/* Primary Intake Camera Scanner Action */}
      <View style={{ marginBottom: spacing.lg }}>
        <Button
          title={`📷  ${t.scanner.capture}`}
          onPress={() => openScanner('general')}
          variant="primary"
          size="lg"
          style={{ width: '100%' }}
        />
      </View>

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
});
