import { test, describe } from 'node:test';
import assert from 'node:assert';
import {
  ENCRYPTED_EXTENSION,
  PackageCryptoError,
  decryptPackage,
  encryptPackage,
  passwordProblem,
} from '../app/lib/packageCrypto';

// A low iteration count keeps the suite fast; the production default is exercised by one test.
const FAST = 1000;
const ITER_OFFSET = 10; // magic (9) + version (1)
const sample = new TextEncoder().encode("%PDF-1.4 synthetic demo bytes");

describe('client-side package encryption (#101)', () => {
  test('round-trips the exact bytes', async () => {
    const sealed = await encryptPackage(sample, "correct horse", FAST);
    assert.deepStrictEqual(Array.from(await decryptPackage(sealed, "correct horse")), Array.from(sample));
  });

  test('ciphertext hides the plaintext and differs on every run (random salt and IV)', async () => {
    const a = await encryptPackage(sample, "correct horse", FAST);
    const b = await encryptPackage(sample, "correct horse", FAST);
    assert.notDeepStrictEqual(Array.from(a), Array.from(b));
    assert.ok(!Buffer.from(a).includes(Buffer.from("synthetic demo bytes")));
  });

  test('a wrong password is rejected', async () => {
    const sealed = await encryptPackage(sample, "correct horse", FAST);
    await assert.rejects(decryptPackage(sealed, "wrong horse!"), PackageCryptoError);
  });

  test('a flipped ciphertext byte is rejected', async () => {
    const sealed = await encryptPackage(sample, "correct horse", FAST);
    sealed[sealed.length - 1] ^= 1;
    await assert.rejects(decryptPackage(sealed, "correct horse"), PackageCryptoError);
  });

  test('tampering with the header (iteration count) is rejected, not silently honoured', async () => {
    const sealed = await encryptPackage(sample, "correct horse", FAST);
    new DataView(sealed.buffer).setUint32(ITER_OFFSET, FAST + 1, false);
    await assert.rejects(decryptPackage(sealed, "correct horse"), PackageCryptoError);
  });

  test('refuses non-ArogyaRakshak files and absurd iteration counts', async () => {
    await assert.rejects(decryptPackage(new Uint8Array(100), "correct horse"), /not an ArogyaRakshak/);
    const sealed = await encryptPackage(sample, "correct horse", FAST);
    new DataView(sealed.buffer).setUint32(ITER_OFFSET, 0xffffffff, false);
    await assert.rejects(decryptPackage(sealed, "correct horse"), /invalid protection settings/);
  });

  test('short passwords are refused before any work is done', async () => {
    assert.ok(passwordProblem("short"));
    assert.strictEqual(passwordProblem("long enough"), null);
    await assert.rejects(encryptPackage(sample, "short", FAST), PackageCryptoError);
  });

  test('works with the production iteration count', async () => {
    const sealed = await encryptPackage(sample, "correct horse");
    assert.deepStrictEqual(Array.from(await decryptPackage(sealed, "correct horse")), Array.from(sample));
    assert.strictEqual(ENCRYPTED_EXTENSION, ".arenc");
  });
});
