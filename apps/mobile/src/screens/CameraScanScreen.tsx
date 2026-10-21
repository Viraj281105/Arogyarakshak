import React, { useState, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/types';
import { DocumentScanType } from '../services/scanner';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { Badge } from '../components';
import { PermissionGate } from './camera/PermissionGate';
import { DocumentTypeTabs, ScanStatusOverlay, Viewfinder } from './camera/ScanOverlays';
import { cameraStyles as styles } from './camera/styles';
import { useScanUpload } from './camera/useScanUpload';

type CameraRouteProp = RouteProp<RootStackParamList, 'CameraScan'>;

/** Document scanner: permission gate, live camera with framing guides, consent-gated
 *  shutter. Upload and navigation live in `useScanUpload`. */
export const CameraScanScreen: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute<CameraRouteProp>();
  const { colors, spacing, typography } = useTheme();
  const { t } = useLanguage();

  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView>(null);

  const [documentType, setDocumentType] = useState<DocumentScanType>(
    route.params?.documentType || 'bill'
  );
  const [flashOn, setFlashOn] = useState(false);
  const [isCameraReady, setIsCameraReady] = useState(false);
  // Opt-IN: the shutter stays disabled until the patient actively consents.
  const [consentGiven, setConsentGiven] = useState(false);
  const { isCapturing, uploadStatus, errorMessage, clearError, handleCapture } = useScanUpload(
    documentType,
    consentGiven,
    t.scanner.consentRequired
  );

  const capture = () =>
    handleCapture(
      cameraRef.current && isCameraReady ? () => cameraRef.current!.takePictureAsync({ quality: 0.85 }) : null
    );

  // 1-2. Permission loading, or permission denied / needed.
  if (!permission || !permission.granted) {
    return <PermissionGate loading={!permission} onRequest={requestPermission} onCancel={() => navigation.goBack()} />;
  }

  // 3. Active Real Hardware Camera View
  return (
    <SafeAreaView style={[styles.container, { backgroundColor: '#000000' }]}>
      {/* Real Expo-Camera Hardware View */}
      <CameraView
        ref={cameraRef}
        style={StyleSheet.absoluteFillObject}
        facing="back"
        enableTorch={flashOn}
        onCameraReady={() => setIsCameraReady(true)}
      />

      {/* Top Controls Bar */}
      <View style={[styles.topBar, { paddingHorizontal: spacing.md }]}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          accessible={true}
          accessibilityRole="button"
          accessibilityLabel="Close scanner"
          style={[styles.iconButton, { minHeight: spacing.minTouchTarget, minWidth: spacing.minTouchTarget }]}
        >
          <Text style={styles.iconText}>✕</Text>
        </TouchableOpacity>

        <Badge label="BYOD Zero Retention" variant="brand" />

        <TouchableOpacity
          onPress={() => setFlashOn((prev) => !prev)}
          accessible={true}
          accessibilityRole="button"
          accessibilityLabel={flashOn ? 'Turn flash off' : 'Turn flash on'}
          style={[styles.iconButton, { minHeight: spacing.minTouchTarget, minWidth: spacing.minTouchTarget }]}
        >
          <Text style={styles.iconText}>{flashOn ? '⚡' : '🔦'}</Text>
        </TouchableOpacity>
      </View>

      <DocumentTypeTabs value={documentType} onChange={setDocumentType} />
      <Viewfinder />

      {(isCapturing || uploadStatus || errorMessage) && (
        <ScanStatusOverlay uploadStatus={uploadStatus} errorMessage={errorMessage} onRetry={clearError} />
      )}

      {/* Bottom Shutter & Controls Section */}
      <View style={[styles.bottomControls, { paddingVertical: spacing.lg }]}>
        <Text style={[styles.byodNotice, { fontSize: typography.sizes.xs }]}>
          🔒 {t.scanner.transientMemoryNotice}
        </Text>

        <TouchableOpacity
          onPress={() => setConsentGiven((prev) => !prev)}
          accessible={true}
          accessibilityRole="checkbox"
          accessibilityState={{ checked: consentGiven }}
          accessibilityLabel={t.scanner.consentText}
          style={styles.consentRow}
        >
          <View
            style={[
              styles.consentBox,
              {
                borderColor: colors.brandCyan,
                backgroundColor: consentGiven ? colors.brandCyan : 'transparent',
              },
            ]}
          />
          <Text style={[styles.consentLabel, { fontSize: typography.sizes.xs }]}>
            {t.scanner.consentText}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          onPress={capture}
          disabled={isCapturing || !consentGiven}
          accessible={true}
          accessibilityRole="button"
          accessibilityLabel={t.scanner.capture}
          style={[
            styles.shutterButton,
            {
              borderColor: colors.brandCyan,
              backgroundColor: isCapturing ? colors.brandCyan : 'rgba(255, 255, 255, 0.25)',
              opacity: consentGiven ? 1 : 0.4,
            },
          ]}
        >
          <View style={[styles.shutterInner, { backgroundColor: colors.brandCyan }]} />
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
};
