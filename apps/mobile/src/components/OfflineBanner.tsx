import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '../theme';
import { offlineBannerSwatch } from './ui/tones';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { useLanguage } from '../hooks/useLanguage';

export const OfflineBanner: React.FC = () => {
  const { colors, spacing, typography } = useTheme();
  // Amber pair from the evidence tokens (tones.ts, AA-checked). Black on light statusWarning was 3.74:1.
  const swatch = offlineBannerSwatch(colors);
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
          backgroundColor: swatch.bg ?? undefined,
          borderBottomColor: swatch.border ?? undefined,
          borderBottomWidth: 1,
          paddingVertical: spacing.xs,
          paddingHorizontal: spacing.md,
        },
      ]}
      accessible={true}
      accessibilityRole="alert"
    >
      <Text style={[styles.text, { fontSize: typography.sizes.xs, color: swatch.fg }]}>
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
    fontWeight: '600',
    textAlign: 'center',
  },
});
