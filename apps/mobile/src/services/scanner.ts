/**
 * ArogyaRakshak Document Scanner Foundation Service
 * Provides camera permission checking, document boundary definitions,
 * and transient memory image management adhering to the Zero-Retention (BYOD) policy.
 */

export type DocumentScanType = 'bill' | 'prescription' | 'denial' | 'general';

export interface ScanDocumentOptions {
  documentType: DocumentScanType;
  flashMode?: 'off' | 'on';
}

export interface ScannedDocument {
  uri: string;
  width?: number;
  height?: number;
  mimeType: string;
  timestamp: number;
  documentType: DocumentScanType;
}

export const scannerService = {
  /**
   * Validate image before submitting to Kadi pipeline
   */
  validateScan: (doc: ScannedDocument): { valid: boolean; reason?: string } => {
    if (!doc.uri) {
      return { valid: false, reason: 'Invalid or missing image URI' };
    }
    return { valid: true };
  },

  /**
   * Prepare transient document payload for Kadi BYOD ingestion.
   * Under BYOD policy, the file is processed transiently and purged.
   */
  createUploadPayload: (
    doc: ScannedDocument
  ): { uri: string; name: string; type: string } => {
    const filename = `${doc.documentType}_${Date.now()}.jpg`;
    return {
      uri: doc.uri,
      name: filename,
      type: doc.mimeType || 'image/jpeg',
    };
  },
};
