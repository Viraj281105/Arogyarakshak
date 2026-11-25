import { describe, it } from 'node:test';
import assert from 'node:assert';
import { clearCaseAccessToken, getCaseAccessToken, setCaseAccessToken, storedCaseTokens } from '../src/api/caseAuth';

describe('Saved keys of older cases (ADR-009, claim only since ADR-029)', () => {
  it('stores, lists and removes keys per case', () => {
    setCaseAccessToken('CASE-a', 'token-a');
    setCaseAccessToken('CASE-b', 'token-b');
    assert.strictEqual(getCaseAccessToken('CASE-a'), 'token-a');
    assert.deepStrictEqual(new Map(storedCaseTokens()).get('CASE-b'), 'token-b');
    clearCaseAccessToken('CASE-a');
    assert.strictEqual(getCaseAccessToken('CASE-a'), undefined);
  });
});
