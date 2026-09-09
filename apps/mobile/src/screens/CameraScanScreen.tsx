import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  Platform,
} from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/types';
import { DocumentScanType, scannerService } from '../services/scanner';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { Badge, Button } from '../components';

type CameraRouteProp = RouteProp<RootStackParamList, 'CameraScan'>;

export const CameraScanScreen: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute<CameraRouteProp>();
  const { colors, spacing, typography, radii } = useTheme();
  const { t } = useLanguage();

  const [documentType, setDocumentType] = useState<DocumentScanType>(
    route.params?.documentType || 'bill'
  );
  const [flashOn, setFlashOn] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);

  const handleCapture = () => {
    setIsCapturing(true);

    // Document Scanning Foundation:
    // Under the Zero-Retention (BYOD) policy, captured image data is processed transiently
    // in memory and transferred to Kadi for entity extraction without permanent storage.
    setTimeout(() => {
      const mockScannedDoc = {
        uri: 'file:///transient_cache/scanned_doc.jpg',
        mimeType: 'image/jpeg',
        timestamp: Date.now(),
        documentType,
      };

      if (route.params?.onScanComplete) {
        route.params.onScanComplete(mockScannedDoc);
      }

      setIsCapturing(false);
      navigation.goBack();
    }, 800);
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: '#000000' }]}>
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
                  backgroundColor: isActive ? 'rgba(6, 182, 212, 0.25)' : 'rgba(255, 255, 255, 0.1)',
                  borderColor: isActive ? colors.brandCyan : 'transparent',
                  minHeight: spacing.minTouchTarget, // 44px
                },
              ]}
            >
              <Text
                style={[
                  styles.typeTabText,
                  {
                    color: isActive ? colors.brandCyan : '#ffffff',
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
              backgroundColor: isCapturing ? colors.brandCyan : 'rgba(255, 255, 255, 0.2)',
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
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: Platform.OS === 'android' ? 16 : 8,
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
    backgroundColor: 'rgba(0, 0, 0, 0.65)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    overflow: 'hidden',
  },
  bottomControls: {
    alignItems: 'center',
    justifyContent: 'center',
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
