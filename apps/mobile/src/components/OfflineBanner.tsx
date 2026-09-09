import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '../theme';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { useLanguage } from '../hooks/useLanguage';

export const OfflineBanner: React.FC = () => {
  const { colors, spacing, typography } = useTheme();
  const { isOnline } = useNetworkStatus();
  const { t } = useLanguage();

  if (isOnline) {
    return null;
  }

  return (
    <View
      style={[
        styles.banner,
        {
          backgroundColor: colors.statusWarning,
          paddingVertical: spacing.xs,
          paddingHorizontal: spacing.md,
        },
      ]}
      accessible={true}
      accessibilityRole="alert"
    >
      <Text style={[styles.text, { fontSize: typography.sizes.xs }]}>
        ⚠️ {t.offlineNotice} — {t.offlineSubtext}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  banner: {
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 999,
  },
  text: {
    color: '#000000',
    fontWeight: '600',
    textAlign: 'center',
  },
});
