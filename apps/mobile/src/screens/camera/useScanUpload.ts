import { useState } from 'react';
import * as FileSystem from 'expo-file-system';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../../navigation/types';
import { DocumentScanType, scannerService, ScannedDocument } from '../../services/scanner';
import { setActiveCaseId } from '../../services/activeCase';

type CameraRouteProp = RouteProp<RootStackParamList, 'CameraScan'>;

// Which module tab opens after a scan of each kind (when the opener did not ask for one).
// Anything else — a bill, a general document — goes to BillNyay.
const SCAN_DESTINATION: Partial<Record<DocumentScanType, 'BillNyay' | 'BimaNyay' | 'DawaCheck'>> = {
  bill: 'BillNyay',
  general: 'BillNyay',
  denial: 'BimaNyay',
  prescription: 'DawaCheck',
};

/**
 * Consent-gated capture and upload of one scanned document, then navigation to the module
 * that should receive the case. The on-device photo is deleted whether or not the upload
 * succeeded.
 */
export function useScanUpload(documentType: DocumentScanType, consentGiven: boolean, consentRequiredMessage: string) {
  const navigation = useNavigation();
  const route = useRoute<CameraRouteProp>();
  const [isCapturing, setIsCapturing] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const performUpload = async (scannedDoc: ScannedDocument) => {
    try {
      setUploadStatus('Creating secure case session in Kadi...');
      const result = await scannerService.processScanAndUpload(scannedDoc, {
        consent: consentGiven,
      });

      setUploadStatus('Document uploaded. Expunging transient memory...');
      // Every module tab now works on this case (DaaviSetu/DawaCheck/BimaNyay no longer
      // need their own scan to receive it).
      setActiveCaseId(result.caseId);

      if (route.params?.onScanComplete) {
        route.params.onScanComplete({
          case_id: result.caseId,
          uploadResponse: result.uploadResponse,
          documentType,
          uri: scannedDoc.uri,
        });
      }

      const params = { caseId: result.caseId, scanCompleted: true };
      if (route.params?.returnTo) {
        // The screen that opened the scanner gets the case back (e.g. DaaviSetu, which
        // used to be sent to BillNyay and so never received a case at all).
        (navigation as any).navigate('MainTabs', { screen: route.params.returnTo, params });
      } else {
        (navigation as any).navigate('MainTabs', { screen: SCAN_DESTINATION[documentType] ?? 'BillNyay', params });
      }
    } catch (err: any) {
      console.warn('[CameraScan] Upload failed:', err);
      setErrorMessage(err.message || 'Failed to upload document to Kadi layer');
    } finally {
      // The status message above says "Expunging transient memory...": takePictureAsync()
      // writes the photo to the device cache, so it is deleted here, in `finally`, on both
      // outcomes. (The server-side BYOD zero-retention claim, ADR-003, never covered this
      // on-device copy; leaving a photographed medical document in app cache would be a
      // local privacy gap of its own.)
      if (scannedDoc.uri && scannedDoc.uri.startsWith('file://')) {
        try {
          await FileSystem.deleteAsync(scannedDoc.uri, { idempotent: true });
        } catch (cleanupErr) {
          console.warn('[CameraScan] Failed to delete cached photo:', cleanupErr);
        }
      }
      setIsCapturing(false);
      setUploadStatus(null);
    }
  };

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

  const handleCapture = async (takePicture: (() => Promise<{ uri: string; width?: number; height?: number } | undefined>) | null) => {
    if (!consentGiven) {
      setErrorMessage(consentRequiredMessage);
      return;
    }

    if (isCapturing) return;
    setIsCapturing(true);
    setErrorMessage(null);

    try {
      if (takePicture) {
        setUploadStatus('Capturing high-resolution document photo...');
        const photo = await takePicture();

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

  return { isCapturing, uploadStatus, errorMessage, clearError: () => setErrorMessage(null), handleCapture };
}
