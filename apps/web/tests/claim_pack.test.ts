import { test, describe } from 'node:test';
import assert from 'node:assert';
import { ClaimPackError, claimPackPath, fetchClaimPack } from '../app/lib/claimPack';
import { decryptPackage } from '../app/lib/packageCrypto';

const ZIP = new Uint8Array([0x50, 0x4b, 0x03, 0x04, 1, 2, 3]);
const okFetch = (seen: { url?: string; headers?: Record<string, string> }) =>
  (async (url: string, init?: RequestInit) => {
    seen.url = url;
    seen.headers = init?.headers as Record<string, string>;
    return new Response(ZIP, { status: 200 });
  }) as unknown as typeof fetch;

describe('Claim Pack download (ADR-015)', () => {
  test('calls the case-scoped route with the access token header, never in the URL', async () => {
    const seen: { url?: string; headers?: Record<string, string> } = {};
    const file = await fetchClaimPack('http://api', 'CASE-1', 'tok-123', { fetchImpl: okFetch(seen) });
    assert.strictEqual(seen.url, 'http://api/api/v1/kadi/cases/CASE-1/claim-pack');
    assert.strictEqual(seen.headers?.['X-Case-Access-Token'], 'tok-123');
    assert.ok(!seen.url!.includes('tok-123'));
    assert.strictEqual(file.filename, 'claim_pack_CASE-1.zip');
    assert.deepStrictEqual(Array.from(file.bytes), Array.from(ZIP));
  });

  test('with a password the bytes are sealed locally and round-trip; the password is not sent', async () => {
    const seen: { url?: string; headers?: Record<string, string> } = {};
    const file = await fetchClaimPack('http://api', 'CASE-1', 'tok', {
      password: 'correct horse', fetchImpl: okFetch(seen), iterations: 1000,
    });
    assert.ok(file.filename.endsWith('.arenc'));
    assert.notDeepStrictEqual(Array.from(file.bytes.slice(0, 4)), Array.from(ZIP.slice(0, 4)));
    assert.deepStrictEqual(Array.from(await decryptPackage(file.bytes, 'correct horse')), Array.from(ZIP));
    assert.ok(!JSON.stringify(seen).includes('correct horse'));
  });

  test('surfaces the API {detail, message} error text', async () => {
    const failing = (async () =>
      new Response(JSON.stringify({ detail: 'consent', message: 'Consent is required.' }), { status: 403 })) as unknown as typeof fetch;
    await assert.rejects(fetchClaimPack('http://api', 'C', 't', { fetchImpl: failing }), (e) => {
      assert.ok(e instanceof ClaimPackError);
      assert.strictEqual((e as Error).message, 'Consent is required.');
      return true;
    });
  });

  test('path is URL-safe', () => {
    assert.strictEqual(claimPackPath('a/b'), '/api/v1/kadi/cases/a%2Fb/claim-pack');
  });
});
