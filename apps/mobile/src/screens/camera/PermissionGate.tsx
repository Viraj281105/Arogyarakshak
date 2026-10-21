import React from 'react';
import { ActivityIndicator, SafeAreaView, Text, View } from 'react-native';
import { useTheme } from '../../theme';
import { useLanguage } from '../../hooks/useLanguage';
import { Badge, Button } from '../../components';
import { cameraStyles as styles } from './styles';

/** Shown while the camera permission is unknown (loading) or not granted (request it). */
export const PermissionGate: React.FC<{ loading: boolean; onRequest: () => void; onCancel: () => void }> = ({
  loading,
  onRequest,
  onCancel,
}) => {
  const { colors, spacing, typography, radii } = useTheme();
  const { t } = useLanguage();

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.bgBase, justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator size="large" color={colors.brandCyan} />
        <Text style={{ color: colors.textSecondary, marginTop: spacing.md, fontSize: typography.sizes.sm }}>
          {t.common.loading}
        </Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.bgBase, padding: spacing.lg, justifyContent: 'center' }]}>
      <View style={[styles.permissionCard, { backgroundColor: colors.bgSurface, borderColor: colors.borderSubtle, borderRadius: radii.lg, padding: spacing.lg }]}>
        <Text style={{ fontSize: 36, textAlign: 'center', marginBottom: spacing.md }}>📷</Text>
        <Text style={[styles.permissionTitle, { color: colors.textPrimary, fontSize: typography.sizes.lg, fontWeight: typography.weights.bold, textAlign: 'center' }]}>
          {t.scanner.cameraPermissionTitle}
        </Text>
        <Text style={[styles.permissionMsg, { color: colors.textSecondary, fontSize: typography.sizes.sm, lineHeight: typography.lineHeights.sm, marginVertical: spacing.md, textAlign: 'center' }]}>
          {t.scanner.cameraPermissionMsg}
        </Text>
        <Badge label="BYOD Zero Retention" variant="brand" style={{ alignSelf: 'center', marginBottom: spacing.lg }} />

        <Button
          title={t.scanner.grantPermission}
          onPress={onRequest}
          variant="primary"
          size="lg"
          style={{ width: '100%', marginBottom: spacing.sm }}
        />
        <Button
          title={t.common.cancel}
          onPress={onCancel}
          variant="secondary"
          size="md"
          style={{ width: '100%' }}
        />
      </View>
    </SafeAreaView>
  );
};
