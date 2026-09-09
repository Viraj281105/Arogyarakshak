import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { Card, Button, Badge } from '../components';

type NavigationProp = NativeStackNavigationProp<RootStackParamList>;

export const SchemeSetuScreen: React.FC = () => {
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
          🏛️ {t.modules.schemesetu.title}
        </Text>
        <Badge label={t.modules.schemesetu.statutory} variant="success" />
      </View>

      <Text style={[styles.desc, { color: colors.textSecondary, fontSize: typography.sizes.sm }]}>
        {t.modules.schemesetu.desc}
      </Text>

      <Card style={{ marginVertical: spacing.md }}>
        <Text style={[styles.cardTitle, { color: colors.textPrimary, fontSize: typography.sizes.md }]}>
          Government Healthcare Welfare Evaluation
        </Text>
        <Text style={[styles.cardBody, { color: colors.textSecondary, fontSize: typography.sizes.sm, marginVertical: spacing.sm }]}>
          Evaluate coverage eligibility for Ayushman Bharat (PM-JAY up to ₹5 Lakhs) and Maharashtra Mahatma Jyotirao Phule Jan Arogya Yojana (MJPJAY), and discover empanelled network hospitals.
        </Text>
        <Button
          title={t.modules.schemesetu.cta}
          onPress={() => navigation.navigate('CameraScan', { documentType: 'general' })}
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
