import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { Card, Button, Badge } from '../components';

type NavigationProp = NativeStackNavigationProp<RootStackParamList>;

export const BimaNyayScreen: React.FC = () => {
  const navigation = useNavigation<NavigationProp>();
  const { colors, spacing, typography } = useTheme();
  const { t } = useLanguage();

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.bgBase }]}
      contentContainerStyle={[styles.content, { padding: spacing.md }]}
    >
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.textPrimary, fontSize: typography.sizes.xl }]}>
          🛡️ {t.modules.bimanyay.title}
        </Text>
        <Badge label={t.modules.bimanyay.statutory} variant="danger" />
      </View>

      <Text style={[styles.desc, { color: colors.textSecondary, fontSize: typography.sizes.sm }]}>
        {t.modules.bimanyay.desc}
      </Text>

      <Card style={{ marginVertical: spacing.md }}>
        <Text style={[styles.cardTitle, { color: colors.textPrimary, fontSize: typography.sizes.md }]}>
          Statutory 3-Tier Claim Denial Dispute
        </Text>
        <Text style={[styles.cardBody, { color: colors.textSecondary, fontSize: typography.sizes.sm, marginVertical: spacing.sm }]}>
          Audit claim repudiation letters against the IRDAI Master Circular (May 29, 2024), enforce the 5-Year Moratorium rule (Clause 16), and auto-draft 3-tier escalation letters (GRO Appeal, Bima Bharosa complaint under 2,000 characters, and Ombudsman Form VI).
        </Text>
        <Button
          title={t.modules.bimanyay.cta}
          onPress={() => navigation.navigate('CameraScan', { documentType: 'denial' })}
          variant="primary"
          style={{ marginTop: spacing.xs }}
        />
      </Card>
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
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  title: {
    fontWeight: '700',
  },
  desc: {
    lineHeight: 22,
  },
  cardTitle: {
    fontWeight: '600',
  },
  cardBody: {
    lineHeight: 20,
  },
});
