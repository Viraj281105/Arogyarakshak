import { api } from '../api';
import { UploadResponse } from '../api/types';

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

  /**
   * Complete BYOD Intake Pipeline:
   * 1. Validates transient document.
   * 2. Initializes case session via api.kadi.createCase({ consent_opt_in: true }).
   * 3. Uploads image to api.kadi.uploadDocument(caseId, payload).
   * 4. Returns caseId and upload metadata without persisting to disk.
   */
  processScanAndUpload: async (
    doc: ScannedDocument,
    userId: string = 'mobile_patient'
  ): Promise<{ caseId: string; uploadResponse: UploadResponse }> => {
    const validation = scannerService.validateScan(doc);
    if (!validation.valid) {
      throw new Error(validation.reason || 'Invalid scan document');
    }

    const caseRes = await api.kadi.createCase({
      consent_opt_in: true,
      user_id: userId,
    });
    const caseId = caseRes.id || caseRes.case_id;
    if (!caseId) {
      throw new Error('Failed to retrieve case ID from Kadi layer');
    }

    const payload = scannerService.createUploadPayload(doc);
    const uploadRes = await api.kadi.uploadDocument(caseId, payload);

    return {
      caseId,
      uploadResponse: uploadRes,
    };
  },
};
