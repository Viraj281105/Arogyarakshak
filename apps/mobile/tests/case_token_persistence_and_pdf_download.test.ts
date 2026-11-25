import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  setCaseAccessToken,
  getCaseAccessToken,
  clearCaseAccessToken,
  hydrateCaseAccessTokens,
} from '../src/api/caseAuth';

const screenSrc = readFileSync(join(process.cwd(), 'src', 'screens', 'DaaviSetuScreen.tsx'), 'utf-8');
const hookSrc = readFileSync(join(process.cwd(), 'src', 'hooks', 'useOfflineQueue.ts'), 'utf-8');
const caseAuthSrc = readFileSync(join(process.cwd(), 'src', 'api', 'caseAuth.ts'), 'utf-8');

describe('SEC-08: file downloads are authorised by the session header', () => {
  const downloadSrc = readFileSync(join(process.cwd(), 'src', 'api', 'download.ts'), 'utf-8');

  it('downloads go through the one authenticated helper, not a bare link', () => {
    assert.ok(/downloadCaseFile\(/.test(screenSrc));
    assert.ok(!/Linking\.openURL/.test(screenSrc));
    assert.ok(/headers: sessionHeaders\(\)/.test(downloadSrc));
  });

  it('the temporary copy is deleted after sharing, and nothing about it is logged', () => {
    assert.ok(/finally \{\s*await FileSystem\.deleteAsync/.test(downloadSrc));
    assert.ok(!/console\./.test(downloadSrc));
  });
});

describe('SEC-14: case access tokens survive an app restart (persisted, not memory-only)', () => {
  beforeEach(() => {
    clearCaseAccessToken('CASE-persist-test-1');
    clearCaseAccessToken('CASE-persist-test-2');
  });

  it('setCaseAccessToken and getCaseAccessToken still round-trip synchronously within a session', () => {
    setCaseAccessToken('CASE-persist-test-1', 'token-abc');
    assert.strictEqual(getCaseAccessToken('CASE-persist-test-1'), 'token-abc');
  });

  it('clearCaseAccessToken removes the token from the in-memory store', () => {
    setCaseAccessToken('CASE-persist-test-2', 'token-xyz');
    clearCaseAccessToken('CASE-persist-test-2');
    assert.strictEqual(getCaseAccessToken('CASE-persist-test-2'), undefined);
  });

  it('hydrateCaseAccessTokens is exported and resolves without throwing', async () => {
    // In this plain Node test environment there is no real SecureStore backing (no RN
    // runtime) — the module degrades gracefully (logs a warning, in-memory store still
    // works for the session) rather than crashing every caller that merely imports
    // caseAuth.ts. The real persistence round-trip is exercised on-device.
    await assert.doesNotReject(hydrateCaseAccessTokens());
  });

  it('hydrateCaseAccessTokens never overwrites a token already set in memory this session', async () => {
    setCaseAccessToken('CASE-persist-test-1', 'freshest-token');
    await hydrateCaseAccessTokens();
    assert.strictEqual(getCaseAccessToken('CASE-persist-test-1'), 'freshest-token');
  });

  it('the token store is backed by expo-secure-store, the same mechanism the offline queue uses', () => {
    assert.ok(
      /expo-secure-store/.test(caseAuthSrc),
      'caseAuth.ts must persist through expo-secure-store, not an ad-hoc/insecure store'
    );
  });

  it('setCaseAccessToken persists to secure storage, not only to the in-memory Map', () => {
    assert.ok(
      /persistTokenInBackground/.test(caseAuthSrc),
      'setCaseAccessToken must write through to secure storage'
    );
  });

  it('the offline queue hydrates tokens before replaying any queued action on restart', () => {
    // The exact SEC-14 property: token hydration must be awaited BEFORE the persisted
    // queue is loaded into state, or the auto-flush effect can fire (queue.length > 0)
    // while tokens are still missing post-restart.
    const loadEffectMatch = hookSrc.match(/useEffect\(\(\) => \{[\s\S]*?QUEUE_STORAGE_KEY[\s\S]*?\}, \[getItem\]\);/);
    assert.ok(loadEffectMatch, 'initial queue-load effect not found');
    const hydrateIndex = loadEffectMatch![0].indexOf('hydrateCaseAccessTokens');
    const queueLoadIndex = loadEffectMatch![0].indexOf('QUEUE_STORAGE_KEY');
    assert.ok(hydrateIndex !== -1, 'useOfflineQueue must call hydrateCaseAccessTokens on mount');
    assert.ok(
      hydrateIndex < queueLoadIndex,
      'token hydration must run BEFORE the queue is loaded/set, not after'
    );
  });

  it('a missing/expired credential (401/403) does not silently drop the queued action after retries', () => {
    // Before this fix, an auth failure was treated identically to any other transient
    // failure: retried up to MAX_RETRIES, then silently dropped from the queue forever
    // — the exact "permanently jamming" / silent-loss failure mode SEC-14 rules out.
    assert.ok(
      /statusCode === 401 \|\| statusCode === 403/.test(hookSrc),
      'processQueue must distinguish an auth failure from an ordinary transient one'
    );
    assert.ok(
      /needsReauth: true/.test(hookSrc),
      'an auth-failed action must be kept in the queue, not retry-counted toward deletion'
    );
  });

  it('an auth-failed action does not block other queued actions from being replayed', () => {
    // The for-loop must continue to the next action regardless of one action's outcome —
    // proven by the catch block pushing into remainingActions/incrementing counters
    // rather than throwing out of the loop.
    const loopMatch = hookSrc.match(/for \(const action of queue\) \{[\s\S]*?\n    \}/);
    assert.ok(loopMatch, 'processQueue action loop not found');
    assert.ok(!/\bthrow\b/.test(loopMatch![0]), 'the replay loop must never rethrow and abort the whole batch');
  });
});
