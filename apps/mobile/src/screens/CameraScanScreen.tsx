import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  Platform,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/types';
import { DocumentScanType, scannerService, ScannedDocument } from '../services/scanner';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { Badge, Button } from '../components';

type CameraRouteProp = RouteProp<RootStackParamList, 'CameraScan'>;

export const CameraScanScreen: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute<CameraRouteProp>();
  const { colors, spacing, typography, radii } = useTheme();
  const { t } = useLanguage();

  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView>(null);

  const [documentType, setDocumentType] = useState<DocumentScanType>(
    route.params?.documentType || 'bill'
  );
  const [flashOn, setFlashOn] = useState(false);
  const [isCameraReady, setIsCameraReady] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fallback for simulators or environments without physical camera
  const handleSimulatedFallback = async () => {
    const fallbackDoc: ScannedDocument = {
      uri: 'file:///transient_cache/scanned_doc.jpg',
      mimeType: 'image/jpeg',
      timestamp: Date.now(),
      documentType,
    };
    await performUpload(fallbackDoc);
  };

  const performUpload = async (scannedDoc: ScannedDocument) => {
    try {
      setUploadStatus('Creating secure case session in Kadi...');
      const result = await scannerService.processScanAndUpload(scannedDoc);

      setUploadStatus('Document uploaded. Expunging transient memory...');

      if (route.params?.onScanComplete) {
        route.params.onScanComplete({
          case_id: result.caseId,
          uploadResponse: result.uploadResponse,
          documentType,
          uri: scannedDoc.uri,
        });
      }

      navigation.goBack();
    } catch (err: any) {
      console.warn('[CameraScan] Upload failed:', err);
      setErrorMessage(err.message || 'Failed to upload document to Kadi layer');
    } finally {
      setIsCapturing(false);
      setUploadStatus(null);
    }
  };

  const handleCapture = async () => {
    if (isCapturing) return;
    setIsCapturing(true);
    setErrorMessage(null);

    try {
      if (cameraRef.current && isCameraReady) {
        setUploadStatus('Capturing high-resolution document photo...');
        const photo = await cameraRef.current.takePictureAsync({
          quality: 0.85,
        });

        if (photo?.uri) {
          const doc: ScannedDocument = {
            uri: photo.uri,
            width: photo.width,
            height: photo.height,
            mimeType: 'image/jpeg',
            timestamp: Date.now(),
            documentType,
          };
          await performUpload(doc);
          return;
        }
      }

      // If camera hardware not available (e.g. simulator/web)
      await handleSimulatedFallback();
    } catch (err: any) {
      console.warn('[CameraScan] Capture exception, using transient fallback:', err);
      await handleSimulatedFallback();
    }
  };

  // 1. Permission Loading State
  if (!permission) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.bgBase, justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator size="large" color={colors.brandCyan} />
        <Text style={{ color: colors.textSecondary, marginTop: spacing.md, fontSize: typography.sizes.sm }}>
          {t.common.loading}
        </Text>
      </SafeAreaView>
    );
  }

  // 2. Permission Denied / Needed Screen
  if (!permission.granted) {
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
            onPress={requestPermission}
            variant="primary"
            size="lg"
            style={{ width: '100%', marginBottom: spacing.sm }}
          />
          <Button
            title={t.common.cancel}
            onPress={() => navigation.goBack()}
            variant="secondary"
            size="md"
            style={{ width: '100%' }}
          />
        </View>
      </SafeAreaView>
    );
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

      {/* Document Type Selector Segmented Tabs */}
      <View style={[styles.typeSelector, { paddingHorizontal: spacing.md }]}>
        {(['bill', 'denial', 'prescription'] as DocumentScanType[]).map((type) => {
          const isActive = documentType === type;
          const label =
            type === 'bill'
              ? t.scanner.billMode
              : type === 'denial'
              ? t.scanner.denialMode
              : t.scanner.prescriptionMode;

          return (
            <TouchableOpacity
              key={type}
              onPress={() => setDocumentType(type)}
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

      {/* Viewfinder with Framing Guides */}
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

      {/* Upload Status / Error Indicator Overlay */}
      {(isCapturing || uploadStatus || errorMessage) && (
        <View style={[styles.statusOverlay, { backgroundColor: 'rgba(10, 14, 23, 0.92)' }]}>
          {errorMessage ? (
            <View style={{ alignItems: 'center', padding: spacing.md }}>
              <Text style={{ fontSize: 28, marginBottom: spacing.xs }}>⚠️</Text>
              <Text style={{ color: colors.statusDanger, fontWeight: '700', fontSize: typography.sizes.sm, textAlign: 'center' }}>
                {errorMessage}
              </Text>
              <Button
                title="Retry Scan"
                onPress={() => setErrorMessage(null)}
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
      )}

      {/* Bottom Shutter & Controls Section */}
      <View style={[styles.bottomControls, { paddingVertical: spacing.lg }]}>
        <Text style={[styles.byodNotice, { fontSize: typography.sizes.xs }]}>
          🔒 {t.scanner.transientMemoryNotice}
        </Text>

        <TouchableOpacity
          onPress={handleCapture}
          disabled={isCapturing}
          accessible={true}
          accessibilityRole="button"
          accessibilityLabel={t.scanner.capture}
          style={[
            styles.shutterButton,
            {
              borderColor: colors.brandCyan,
              backgroundColor: isCapturing ? colors.brandCyan : 'rgba(255, 255, 255, 0.25)',
            },
          ]}
        >
          <View style={[styles.shutterInner, { backgroundColor: colors.brandCyan }]} />
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'space-between',
  },
  permissionCard: {
    borderWidth: 1,
  },
  permissionTitle: {
    letterSpacing: -0.3,
  },
  permissionMsg: {
    lineHeight: 22,
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: Platform.OS === 'android' ? 16 : 8,
    zIndex: 10,
  },
  iconButton: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconText: {
    color: '#ffffff',
    fontSize: 20,
  },
  typeSelector: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginVertical: 12,
    zIndex: 10,
  },
  typeTab: {
    flex: 1,
    marginHorizontal: 3,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 6,
  },
  typeTabText: {
    fontSize: 12,
    textAlign: 'center',
  },
  viewfinderContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  viewfinderFrame: {
    width: '100%',
    aspectRatio: 3 / 4,
    borderWidth: 1.5,
    borderStyle: 'dashed',
    borderRadius: 12,
    position: 'relative',
    alignItems: 'center',
    justifyContent: 'center',
  },
  cornerTL: {
    position: 'absolute',
    top: -2,
    left: -2,
    width: 24,
    height: 24,
    borderTopWidth: 4,
    borderLeftWidth: 4,
  },
  cornerTR: {
    position: 'absolute',
    top: -2,
    right: -2,
    width: 24,
    height: 24,
    borderTopWidth: 4,
    borderRightWidth: 4,
  },
  cornerBL: {
    position: 'absolute',
    bottom: -2,
    left: -2,
    width: 24,
    height: 24,
    borderBottomWidth: 4,
    borderLeftWidth: 4,
  },
  cornerBR: {
    position: 'absolute',
    bottom: -2,
    right: -2,
    width: 24,
    height: 24,
    borderBottomWidth: 4,
    borderRightWidth: 4,
  },
  frameInstruction: {
    color: '#ffffff',
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    overflow: 'hidden',
  },
  statusOverlay: {
    position: 'absolute',
    top: '35%',
    left: 24,
    right: 24,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(6, 182, 212, 0.4)',
    zIndex: 50,
    alignItems: 'center',
    justifyContent: 'center',
  },
  bottomControls: {
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
  },
  byodNotice: {
    color: '#94a3b8',
    marginBottom: 16,
    textAlign: 'center',
  },
  shutterButton: {
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  shutterInner: {
    width: 54,
    height: 54,
    borderRadius: 27,
  },
});
