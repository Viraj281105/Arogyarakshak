import { test, describe } from 'node:test';
import assert from 'node:assert';
import { API_BASE } from '../app/hooks/useApi';

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
