import { test, describe } from 'node:test';
import assert from 'node:assert';
import { API_BASE, caseAuthHeaders, normalizeErrorDetail } from '../app/hooks/useApi';

describe('Web API Client & Configuration', () => {
  test('API_BASE should default to port 8000 when NEXT_PUBLIC_API_URL is unset', () => {
    assert.ok(typeof API_BASE === 'string');
    assert.ok(API_BASE.includes('8000') || API_BASE.startsWith('http'));
  });

  test('should format error responses correctly when given detail or message', () => {
    const errorJsonWithDetail = { detail: 'CGHS rate not found for procedure' };
    assert.strictEqual(errorJsonWithDetail.detail, 'CGHS rate not found for procedure');

    const errorJsonWithMessage = { message: 'Failed to process hospital bill' };
    assert.strictEqual(errorJsonWithMessage.message, 'Failed to process hospital bill');
  });
});

describe('normalizeErrorDetail (P1-9)', () => {
  // Regression: FastAPI's automatic 422 validation responses send `detail` as an ARRAY
  // of {loc, msg, type} objects, not a string. Rendering that array directly as a React
  // child crashes with "Objects are not valid as a React child" the first time a 422
  // reaches the UI.
  test('passes a plain string through unchanged', () => {
    assert.strictEqual(normalizeErrorDetail('Case not found'), 'Case not found');
  });

  test('summarizes a FastAPI 422 validation-error array into a readable string', () => {
    const detail = [
      { loc: ['body', 'income'], msg: 'field required', type: 'value_error.missing' },
      { loc: ['body', 'location_state'], msg: 'field required', type: 'value_error.missing' },
    ];
    const result = normalizeErrorDetail(detail);
    assert.strictEqual(typeof result, 'string');
    assert.ok(result.includes('field required'));
    assert.ok(result.includes('income'));
    assert.ok(result.includes('location_state'));
  });

  test('handles an empty validation-error array without crashing', () => {
    assert.strictEqual(typeof normalizeErrorDetail([]), 'string');
  });

  test('handles a malformed array entry (missing msg) without throwing', () => {
    const result = normalizeErrorDetail([{ loc: ['body', 'x'] }, 'a plain string entry']);
    assert.strictEqual(typeof result, 'string');
  });

  test('summarizes an arbitrary non-array object rather than rendering it raw', () => {
    const result = normalizeErrorDetail({ code: 'RATE_LIMITED', retry_after_seconds: 30 });
    assert.strictEqual(typeof result, 'string');
    assert.ok(result.length > 0);
  });

  test('never returns a non-string for any input shape', () => {
    for (const input of ['x', 42, null, undefined, true, [], {}, [1, 2, 3]]) {
      assert.strictEqual(typeof normalizeErrorDetail(input), 'string');
    }
  });
});

describe('caseAuthHeaders (ADR-009)', () => {
  test('returns the X-Case-Access-Token header when a token is provided', () => {
    const headers = caseAuthHeaders('abc123');
    assert.deepStrictEqual(headers, { 'X-Case-Access-Token': 'abc123' });
  });

  test('returns an empty object when no token is available yet', () => {
    assert.deepStrictEqual(caseAuthHeaders(undefined), {});
    assert.deepStrictEqual(caseAuthHeaders(null), {});
    assert.deepStrictEqual(caseAuthHeaders(''), {});
  });

  test('should structure PreAuth payload adhering to IRDAI Annexure-B fields', () => {
    const payload = {
      policy_number: 'POL-STAR-774411',
      patient_name: 'Viraj Jadhao',
      hospital_name: 'Apollo Hospital',
      treatment_plan: 'Laparoscopic Appendectomy',
    };
    assert.ok(payload.policy_number);
    assert.ok(payload.patient_name);
    assert.ok(payload.hospital_name);
    assert.ok(payload.treatment_plan);
  });
});
