import { afterEach, beforeEach, describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { request } from '../src/api/client';
import { setCaseAccessToken, getCaseAccessToken } from '../src/api/caseAuth';
import { claimStoredCases, getSessionStatus, resetSessionForTests, sessionHeaders, signIn, signOut } from '../src/api/session';

type Call = { url: string; method: string; headers: Record<string, string> };

describe('account session on mobile (ADR-029)', () => {
  const realFetch = globalThis.fetch;
  let calls: Call[] = [];
  let respond: (url: string) => Response;

  beforeEach(() => {
    calls = [];
    respond = () => new Response(JSON.stringify({ token: 'session-1' }), { status: 200 });
    resetSessionForTests();
    globalThis.fetch = (async (url: string, init: { method?: string; headers: Record<string, string> }) => {
      calls.push({ url, method: init.method ?? 'GET', headers: init.headers });
      return respond(url);
    }) as unknown as typeof fetch;
  });
  afterEach(() => {
    globalThis.fetch = realFetch;
  });

  it('signs in with a bearer session and sends it only as a header', async () => {
    await signIn('a@example.org', 'a long enough password');
    assert.strictEqual(getSessionStatus(), 'signed-in');
    calls = [];
    await request('/api/v1/dawacheck/benchmark');
    assert.strictEqual(calls[0].headers.Authorization, 'Bearer session-1');
    assert.ok(!calls[0].url.includes('session-1'));
  });

  it('a 401 from any other route ends the session on the device', async () => {
    resetSessionForTests('signed-in', 'old');
    respond = () => new Response(JSON.stringify({ detail: 'Sign in to continue.' }), { status: 401 });
    await assert.rejects(request('/api/v1/kadi/cases'));
    assert.strictEqual(getSessionStatus(), 'expired');
    assert.deepStrictEqual(sessionHeaders(), {});
  });

  it('a wrong password is an answer, not an expired session', async () => {
    respond = () => new Response(JSON.stringify({ detail: 'Email or password is incorrect.' }), { status: 401 });
    await assert.rejects(signIn('a@example.org', 'wrong password here'));
    assert.strictEqual(getSessionStatus(), 'signed-out');
  });

  it('signing out forgets the session even when the server cannot be reached', async () => {
    resetSessionForTests('signed-in', 's');
    respond = () => {
      throw new TypeError('offline');
    };
    await signOut();
    assert.strictEqual(getSessionStatus(), 'signed-out');
    assert.deepStrictEqual(sessionHeaders(), {});
  });

  it('claims an older case with its saved key, then deletes the key', async () => {
    resetSessionForTests('signed-in', 's');
    setCaseAccessToken('CASE-old', 'old-key');
    respond = () => new Response(JSON.stringify({ claimed: true }), { status: 200 });
    assert.ok((await claimStoredCases()) >= 1);
    const claim = calls.find((c) => c.url.endsWith('/cases/CASE-old/claim'))!;
    assert.strictEqual(claim.headers['X-Case-Access-Token'], 'old-key');
    assert.strictEqual(claim.headers.Authorization, 'Bearer s');
    assert.strictEqual(getCaseAccessToken('CASE-old'), undefined);
  });

  it('no screen or hook puts a credential in a URL', () => {
    for (const file of ['src/hooks/useSSEStream.ts', 'src/screens/DaaviSetuScreen.tsx', 'src/screens/billnyay/AppealCard.tsx', 'src/api/download.ts']) {
      const source = readFileSync(join(process.cwd(), file), 'utf-8');
      assert.ok(!/access_token=|[?&]token=/.test(source), file);
    }
  });

  it('the app shows its screens only behind a signed-in session', () => {
    const app = readFileSync(join(process.cwd(), 'App.tsx'), 'utf-8');
    assert.match(app, /session === 'signed-in' \? \(\s*<NavigationContainer/);
  });
});
