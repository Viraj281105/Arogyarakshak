import React from 'react';
import { ActivityIndicator, Text, TouchableOpacity, View } from 'react-native';
import { useTheme } from '../../theme';
import { useLanguage } from '../../hooks/useLanguage';
import { Button } from '../../components';
import { DocumentScanType } from '../../services/scanner';
import { cameraStyles as styles } from './styles';

/** Bill / denial letter / prescription selector over the camera view. */
export const DocumentTypeTabs: React.FC<{ value: DocumentScanType; onChange: (type: DocumentScanType) => void }> = ({ value, onChange }) => {
  const { colors, spacing } = useTheme();
  const { t } = useLanguage();
  return (
    <View style={[styles.typeSelector, { paddingHorizontal: spacing.md }]}>
      {(['bill', 'denial', 'prescription'] as DocumentScanType[]).map((type) => {
        const isActive = value === type;
        const label =
          type === 'bill'
            ? t.scanner.billMode
            : type === 'denial'
            ? t.scanner.denialMode
            : t.scanner.prescriptionMode;

        return (
          <TouchableOpacity
            key={type}
            onPress={() => onChange(type)}
            style={[
              styles.typeTab,
              {
                backgroundColor: isActive ? 'rgba(6, 182, 212, 0.4)' : 'rgba(0, 0, 0, 0.55)',
                borderColor: isActive ? colors.brandCyan : 'rgba(255, 255, 255, 0.2)',
                minHeight: spacing.minTouchTarget,
              },
            ]}
          >
            <Text
              style={[
                styles.typeTabText,
                {
                  color: isActive ? '#ffffff' : '#e2e8f0',
                  fontWeight: isActive ? '700' : '400',
                },
              ]}
            >
              {label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
};

/** Dashed document frame with corner guides and the framing instruction. */
export const Viewfinder: React.FC = () => {
  const { colors, typography } = useTheme();
  const { t } = useLanguage();
  return (
    <View style={styles.viewfinderContainer}>
      <View style={[styles.viewfinderFrame, { borderColor: colors.brandCyan }]}>
        {/* Corner Guidemarks */}
        <View style={[styles.cornerTL, { borderColor: colors.brandCyan }]} />
        <View style={[styles.cornerTR, { borderColor: colors.brandCyan }]} />
        <View style={[styles.cornerBL, { borderColor: colors.brandCyan }]} />
        <View style={[styles.cornerBR, { borderColor: colors.brandCyan }]} />

        <Text style={[styles.frameInstruction, { fontSize: typography.sizes.xs }]}>
          {t.scanner.instruction}
        </Text>
      </View>
    </View>
  );
};

/** Upload progress or the failure (with retry) over the camera view. */
export const ScanStatusOverlay: React.FC<{ uploadStatus: string | null; errorMessage: string | null; onRetry: () => void }> = ({
  uploadStatus,
  errorMessage,
  onRetry,
}) => {
  const { colors, spacing, typography } = useTheme();
  const { t } = useLanguage();
  return (
    <View style={[styles.statusOverlay, { backgroundColor: 'rgba(10, 14, 23, 0.92)' }]}>
      {errorMessage ? (
        <View style={{ alignItems: 'center', padding: spacing.md }}>
          <Text style={{ fontSize: 28, marginBottom: spacing.xs }}>⚠️</Text>
          <Text style={{ color: colors.statusDanger, fontWeight: '700', fontSize: typography.sizes.sm, textAlign: 'center' }}>
            {errorMessage}
          </Text>
          <Button
            title="Retry Scan"
            onPress={onRetry}
            variant="primary"
            size="sm"
            style={{ marginTop: spacing.md }}
          />
        </View>
      ) : (
        <View style={{ alignItems: 'center', padding: spacing.md }}>
          <ActivityIndicator size="large" color={colors.brandCyan} />
          <Text style={{ color: colors.textPrimary, marginTop: spacing.sm, fontWeight: '600', fontSize: typography.sizes.sm, textAlign: 'center' }}>
            {uploadStatus || t.scanner.process}
          </Text>
          <Text style={{ color: colors.textMuted, fontSize: typography.sizes.xs, marginTop: 4 }}>
            🔒 BYOD Policy: Processed transiently in RAM
          </Text>
        </View>
      )}
    </View>
  );
};
