import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert';
import { request } from '../src/api/client';
import { setCaseAccessToken } from '../src/api/caseAuth';

type Captured = { url: string; headers: Record<string, string> };

describe('mobile request() delegates to the shared api-client', () => {
  const realFetch = globalThis.fetch;
  let captured: Captured[] = [];

  beforeEach(() => {
    captured = [];
    globalThis.fetch = (async (url: string, init: { headers: Record<string, string> }) => {
      captured.push({ url, headers: init.headers });
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    }) as unknown as typeof fetch;
  });
  afterEach(() => {
    globalThis.fetch = realFetch;
  });

  it('attaches the case token on a case path', async () => {
    setCaseAccessToken('CASE-deleg1', 'tok-1');
    await request('/api/v1/billnyay/cases/CASE-deleg1/audit');
    assert.strictEqual(captured[0].headers['X-Case-Access-Token'], 'tok-1');
  });

  it('does NOT attach a case token on a non-case path, even when tokens exist', async () => {
    setCaseAccessToken('CASE-deleg2', 'tok-2');
    await request('/api/v1/dawacheck/benchmark');
    await request('/health');
    for (const c of captured) {
      assert.strictEqual(c.headers['X-Case-Access-Token'], undefined);
      assert.ok(!Object.keys(c.headers).some((k) => k.toLowerCase().includes('token')));
    }
  });

  it('rejects with an ApiError (statusCode 0) on a network failure, never a TypeError', async () => {
    globalThis.fetch = (async () => {
      throw new TypeError('Network request failed');
    }) as unknown as typeof fetch;
    await assert.rejects(request('/health'), (err: unknown) => {
      const e = err as { statusCode?: number; message?: string };
      return !(err instanceof TypeError) && e.statusCode === 0 && e.message === 'Network request failed';
    });
  });

  it('keeps statusCode and a normalised string detail on an HTTP 422', async () => {
    globalThis.fetch = (async () =>
      new Response(JSON.stringify({ detail: [{ loc: ['body', 'x'], msg: 'bad' }] }), { status: 422 })) as unknown as typeof fetch;
    await assert.rejects(request('/x'), (err: unknown) => {
      const e = err as { statusCode?: number; detail?: string };
      return e.statusCode === 422 && e.detail === 'x: bad';
    });
  });
});
