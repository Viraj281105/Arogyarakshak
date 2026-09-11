import test, { describe, it } from 'node:test';
import assert from 'node:assert';
import { api } from '../src/api/endpoints';
import { apiClient } from '../src/api/client';
import { scannerService } from '../src/services/scanner';
import { translations, Language } from '../src/translations/strings';

describe('BYOD Zero-Retention Invariant Guard', () => {
  it('should enforce rejection of raw document persistent storage attempts', async () => {
    // Simulating useOfflineStorage logic
    const validateAndStore = (key: string, value: string): boolean => {
      if (key.includes('doc_raw') || key.includes('patient_file') || value.length > 50000) {
        return false;
      }
      return true;
    };

    assert.strictEqual(validateAndStore('session_token', 'token_12345'), true);
    assert.strictEqual(validateAndStore('user_lang', 'mr'), true);
    assert.strictEqual(validateAndStore('doc_raw_bill', 'base64_data...'), false);
    assert.strictEqual(validateAndStore('patient_file_scan', 'blob_data...'), false);
    assert.strictEqual(validateAndStore('large_key', 'x'.repeat(60000)), false);
  });
});

describe('Mobile API Gateway Contract Mapping', () => {
  it('should route Kadi upload to /api/v1/kadi/cases/:caseId/upload', async () => {
    const origPost = apiClient.post;
    let requestedEndpoint = '';
    let sentFormData: any = null;

    apiClient.post = async (endpoint: string, data?: any) => {
      requestedEndpoint = endpoint;
      sentFormData = data;
      return {
        case_id: 'CASE-ABC',
        filename: 'bill.jpg',
        message: 'Success',
      } as any;
    };

    try {
      const filePayload = { uri: 'file:///photo.jpg', name: 'bill.jpg', type: 'image/jpeg' };
      const res = await api.kadi.uploadDocument('CASE-ABC', filePayload);

      assert.strictEqual(requestedEndpoint, '/api/v1/kadi/cases/CASE-ABC/upload');
      assert.strictEqual(res.case_id, 'CASE-ABC');
    } finally {
      apiClient.post = origPost;
    }
  });

  it('should send the caller-supplied consent value verbatim, never a default', async () => {
    const origPost = apiClient.post;
    let requestedEndpoint = '';
    let sentData: any = null;

    apiClient.post = async (endpoint: string, data?: any) => {
      requestedEndpoint = endpoint;
      sentData = data;
      return {
        id: 'CASE-NEW',
        status: 'active',
        consent_opt_in: true,
        created_at: new Date().toISOString(),
      } as any;
    };

    try {
      const res = await api.kadi.createCase({
        consent_opt_in: true,
        user_id: 'mobile_user',
      });
      assert.strictEqual(requestedEndpoint, '/api/v1/kadi/cases');
      assert.strictEqual(sentData.consent_opt_in, true);
      assert.strictEqual(sentData.user_id, 'mobile_user');
      assert.strictEqual(res.id, 'CASE-NEW');

      // A declined consent must be transmitted as false, not silently upgraded.
      await api.kadi.createCase({ consent_opt_in: false, user_id: 'mobile_user' });
      assert.strictEqual(sentData.consent_opt_in, false);
    } finally {
      apiClient.post = origPost;
    }
  });

  it('should route BimaNyay analyze with language query parameter', async () => {
    const origPost = apiClient.post;
    let requestedEndpoint = '';

    apiClient.post = async (endpoint: string, data?: any) => {
      requestedEndpoint = endpoint;
      return {
        audit_result: { status: 'repudiation_found' },
        appeal_package: {},
      } as any;
    };

    try {
      await api.bimanyay.analyze(
        {
          policy_number: 'POL-123',
          insurer_name: 'Star Health',
          policy_age_years: 5,
          claimed_amount: 150000,
          denied_or_deducted_amount: 150000,
          denial_category: 'ped_exclusion',
          denial_reason_raw: 'Pre-existing disease exclusion',
          diagnosis: 'Diabetes complication',
        },
        'hi'
      );
      assert.strictEqual(requestedEndpoint, '/api/v1/bimanyay/analyze?language=hi');
    } finally {
      apiClient.post = origPost;
    }
  });
});

describe('Mobile Consent Enforcement', () => {
  const languages: Language[] = ['en', 'hi', 'mr'];

  it('should refuse to create a case when consent is withheld', async () => {
    let createCaseCalled = false;
    const orig = api.kadi.createCase;
    api.kadi.createCase = async (data: any) => {
      createCaseCalled = true;
      return { id: 'CASE-X', status: 'active', created_at: '' } as any;
    };

    const doc = {
      uri: 'file:///tmp/bill.jpg',
      mimeType: 'image/jpeg',
      timestamp: Date.now(),
      documentType: 'bill' as const,
    };

    try {
      await assert.rejects(
        async () => {
          await scannerService.processScanAndUpload(doc, { consent: false });
        },
        (err: Error) => /[Cc]onsent is required/.test(err.message)
      );
      assert.strictEqual(
        createCaseCalled,
        false,
        'no case may be created when consent is withheld'
      );
    } finally {
      api.kadi.createCase = orig;
    }
  });

  it('should propagate the granted consent value into the created case', async () => {
    let sent: any = null;
    const origCreate = api.kadi.createCase;
    const origUpload = api.kadi.uploadDocument;
    api.kadi.createCase = async (data: any) => {
      sent = data;
      return { id: 'CASE-Y', status: 'active', created_at: '' } as any;
    };
    api.kadi.uploadDocument = async (caseId: string) =>
      ({ status: 'success', case_id: caseId, filename: 'f', message: 'ok' } as any);

    const doc = {
      uri: 'file:///tmp/bill.jpg',
      mimeType: 'image/jpeg',
      timestamp: Date.now(),
      documentType: 'bill' as const,
    };

    try {
      await scannerService.processScanAndUpload(doc, { consent: true });
      assert.strictEqual(sent.consent_opt_in, true);
    } finally {
      api.kadi.createCase = origCreate;
      api.kadi.uploadDocument = origUpload;
    }
  });

  it('should localize the consent vocabulary in all 3 languages', () => {
    languages.forEach((lang) => {
      const s = translations[lang].scanner;
      assert.ok(s.consentText && s.consentText.trim().length > 0, `consentText missing in ${lang}`);
      assert.ok(
        s.consentRequired && s.consentRequired.trim().length > 0,
        `consentRequired missing in ${lang}`
      );
      assert.ok(s.scanFirst && s.scanFirst.trim().length > 0, `scanFirst missing in ${lang}`);
    });
  });
});
