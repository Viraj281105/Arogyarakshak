import test, { describe, it } from 'node:test';
import assert from 'node:assert';
import { scannerService, ScannedDocument } from '../src/services/scanner';
import { translations } from '../src/translations/strings';
import { api } from '../src/api/endpoints';

describe('Mobile Document Scanner Foundation', () => {
  it('should validate valid scanned document', () => {
    const doc: ScannedDocument = {
      uri: 'file:///transient/photo_123.jpg',
      mimeType: 'image/jpeg',
      timestamp: Date.now(),
      documentType: 'bill',
    };

    const validation = scannerService.validateScan(doc);
    assert.strictEqual(validation.valid, true);
    assert.strictEqual(validation.reason, undefined);
  });

  it('should reject scan with missing URI', () => {
    const invalidDoc = {
      uri: '',
      mimeType: 'image/jpeg',
      timestamp: Date.now(),
      documentType: 'bill',
    } as ScannedDocument;

    const validation = scannerService.validateScan(invalidDoc);
    assert.strictEqual(validation.valid, false);
    assert.strictEqual(validation.reason, 'Invalid or missing image URI');
  });

  it('should create upload payload with correct filename and mimetype', () => {
    const doc: ScannedDocument = {
      uri: 'file:///transient/bill_test.jpg',
      mimeType: 'image/jpeg',
      timestamp: 1700000000000,
      documentType: 'denial',
    };

    const payload = scannerService.createUploadPayload(doc);
    assert.strictEqual(payload.uri, 'file:///transient/bill_test.jpg');
    assert.strictEqual(payload.type, 'image/jpeg');
    assert.ok(payload.name.startsWith('denial_'));
    assert.ok(payload.name.endsWith('.jpg'));
  });

  it('should execute processScanAndUpload by calling kadi.createCase and uploadDocument', async () => {
    const doc: ScannedDocument = {
      uri: 'file:///transient/bill_test.jpg',
      mimeType: 'image/jpeg',
      timestamp: Date.now(),
      documentType: 'bill',
    };

    let createCaseCalled = false;
    let uploadCalledWithCaseId = '';

    // Mock Kadi API endpoints
    const origCreateCase = api.kadi.createCase;
    const origUpload = api.kadi.uploadDocument;

    api.kadi.createCase = async (data?: any) => {
      createCaseCalled = true;
      assert.strictEqual(data?.consent_opt_in, true);
      return {
        id: 'CASE-TEST-1234',
        status: 'active',
        created_at: new Date().toISOString(),
      } as any;
    };

    api.kadi.uploadDocument = async (caseId: string, filePayload: any) => {
      uploadCalledWithCaseId = caseId;
      assert.strictEqual(filePayload.uri, doc.uri);
      return {
        status: 'success',
        case_id: caseId,
        filename: filePayload.name,
        message: 'Mock uploaded successfully',
      };
    };

    try {
      const result = await scannerService.processScanAndUpload(doc, 'test_user');
      assert.strictEqual(createCaseCalled, true);
      assert.strictEqual(uploadCalledWithCaseId, 'CASE-TEST-1234');
      assert.strictEqual(result.caseId, 'CASE-TEST-1234');
      assert.strictEqual(result.uploadResponse.filename.startsWith('bill_'), true);
    } finally {
      // Restore mocks
      api.kadi.createCase = origCreateCase;
      api.kadi.uploadDocument = origUpload;
    }
  });

  it('should reject processScanAndUpload on invalid document', async () => {
    const invalidDoc = { uri: '', documentType: 'bill' } as any;
    await assert.rejects(
      async () => {
        await scannerService.processScanAndUpload(invalidDoc);
      },
      {
        name: 'Error',
        message: 'Invalid or missing image URI',
      }
    );
  });
});

describe('Mobile Trilingual Dictionary Integrity', () => {
  it('should verify all 3 languages have matched tabs and scanner keys', () => {
    const langs = ['en', 'hi', 'mr'] as const;
    for (const lang of langs) {
      const dict = translations[lang];
      assert.ok(dict.appName, `Missing appName in ${lang}`);
      assert.ok(dict.byodBadge, `Missing byodBadge in ${lang}`);
      assert.ok(dict.tabs.home, `Missing tabs.home in ${lang}`);
      assert.ok(dict.tabs.billnyay, `Missing tabs.billnyay in ${lang}`);
      assert.ok(dict.tabs.daavisetu, `Missing tabs.daavisetu in ${lang}`);
      assert.ok(dict.tabs.bimanyay, `Missing tabs.bimanyay in ${lang}`);
      assert.ok(dict.tabs.schemesetu, `Missing tabs.schemesetu in ${lang}`);
      assert.ok(dict.tabs.dawacheck, `Missing tabs.dawacheck in ${lang}`);
      assert.ok(dict.scanner.capture, `Missing scanner.capture in ${lang}`);
      assert.ok(dict.scanner.transientMemoryNotice, `Missing transient notice in ${lang}`);
    }
  });
});
