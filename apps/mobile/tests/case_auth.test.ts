import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert';
import {
  setCaseAccessToken,
  getCaseAccessToken,
  extractCaseIdFromPath,
  tokenHeaderForPath,
} from '../src/api/caseAuth';

describe('Per-case access token store (ADR-009)', () => {
  it('extracts a case id from a case-scoped path', () => {
    assert.strictEqual(
      extractCaseIdFromPath('/api/v1/billnyay/cases/CASE-abcd1234/audit'),
      'CASE-abcd1234'
    );
    assert.strictEqual(
      extractCaseIdFromPath('/api/v1/kadi/cases/CASE-abcd1234/resolutions?status=pending'),
      'CASE-abcd1234'
    );
  });

  it('returns undefined for a path with no case id', () => {
    assert.strictEqual(extractCaseIdFromPath('/api/v1/dawacheck/benchmark'), undefined);
  });

  it('stores and retrieves a token by case id', () => {
    setCaseAccessToken('CASE-test1', 'secret-token-1');
    assert.strictEqual(getCaseAccessToken('CASE-test1'), 'secret-token-1');
  });

  it('builds the X-Case-Access-Token header for a known case', () => {
    setCaseAccessToken('CASE-test2', 'secret-token-2');
    const headers = tokenHeaderForPath('/api/v1/billnyay/cases/CASE-test2/audit');
    assert.deepStrictEqual(headers, { 'X-Case-Access-Token': 'secret-token-2' });
  });

  it('returns no header for a case this session never created', () => {
    // Regression guard for the actual security property: a client that only knows a
    // case id (e.g. copied from a shared link) must not automatically gain its token —
    // the whole point of ADR-009 is that a case id alone is not authorization.
    const headers = tokenHeaderForPath('/api/v1/billnyay/cases/CASE-never-created/audit');
    assert.deepStrictEqual(headers, {});
  });

  it('returns no header for a path with no case id at all', () => {
    setCaseAccessToken('CASE-test3', 'secret-token-3');
    assert.deepStrictEqual(tokenHeaderForPath('/api/v1/dawacheck/benchmark'), {});
  });

  it('different cases get independently retrievable tokens', () => {
    setCaseAccessToken('CASE-a', 'token-a');
    setCaseAccessToken('CASE-b', 'token-b');
    assert.strictEqual(getCaseAccessToken('CASE-a'), 'token-a');
    assert.strictEqual(getCaseAccessToken('CASE-b'), 'token-b');
    assert.notStrictEqual(getCaseAccessToken('CASE-a'), getCaseAccessToken('CASE-b'));
  });
});
