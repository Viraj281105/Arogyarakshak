// Client-side password protection for downloaded document packages (issue #101).
//
// The server never sees the password or the ciphertext: the package is fetched, encrypted
// in the browser with the Web Crypto API, and saved locally. This protects the file at rest
// (a lost laptop, an e-mail attachment) - it does not change the zero-retention rule, and
// it is only as strong as the password the patient chooses.
//
// File layout (all binary):
//   magic "AROGYAENC" (9) | version (1) | iterations (4, big-endian) | salt (16) | iv (12) | ciphertext+tag
// The whole header is bound to the ciphertext as AES-GCM additional data, so tampering with
// it makes decryption fail rather than silently using other parameters.
// KDF: PBKDF2-HMAC-SHA256 -> AES-256-GCM.

const MAGIC = new TextEncoder().encode("AROGYAENC");
const VERSION = 1;
const SALT_BYTES = 16;
const IV_BYTES = 12;
const ITER_OFFSET = MAGIC.length + 1;
const SALT_OFFSET = ITER_OFFSET + 4;
const IV_OFFSET = SALT_OFFSET + SALT_BYTES;
const HEADER_BYTES = IV_OFFSET + IV_BYTES;
const GCM_TAG_BYTES = 16;

export const PBKDF2_ITERATIONS = 600_000;
export const MIN_PASSWORD_LENGTH = 8;
export const ENCRYPTED_EXTENSION = ".arenc";

// Upper bound on the iteration count honoured when decrypting, so a crafted file cannot
// make the browser spin on an absurd KDF cost.
const MAX_ITERATIONS = 10_000_000;

export class PackageCryptoError extends Error {}

function subtle(): SubtleCrypto {
  const s = globalThis.crypto?.subtle;
  if (!s) throw new PackageCryptoError("This browser does not support the Web Crypto API.");
  return s;
}

async function deriveKey(password: string, salt: Uint8Array, iterations: number): Promise<CryptoKey> {
  const material = await subtle().importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveKey"]);
  return subtle().deriveKey(
    { name: "PBKDF2", salt: salt as BufferSource, iterations, hash: "SHA-256" },
    material,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
}

function buildHeader(iterations: number, salt: Uint8Array, iv: Uint8Array): Uint8Array {
  const header = new Uint8Array(HEADER_BYTES);
  header.set(MAGIC, 0);
  header[MAGIC.length] = VERSION;
  new DataView(header.buffer).setUint32(ITER_OFFSET, iterations, false);
  header.set(salt, SALT_OFFSET);
  header.set(iv, IV_OFFSET);
  return header;
}

export function passwordProblem(password: string): string | null {
  if (password.length < MIN_PASSWORD_LENGTH) {
    return `Use at least ${MIN_PASSWORD_LENGTH} characters.`;
  }
  return null;
}

export async function encryptPackage(
  data: ArrayBuffer | Uint8Array,
  password: string,
  iterations: number = PBKDF2_ITERATIONS,
): Promise<Uint8Array> {
  const problem = passwordProblem(password);
  if (problem) throw new PackageCryptoError(problem);
  const salt = globalThis.crypto.getRandomValues(new Uint8Array(SALT_BYTES));
  const iv = globalThis.crypto.getRandomValues(new Uint8Array(IV_BYTES));
  const header = buildHeader(iterations, salt, iv);
  const key = await deriveKey(password, salt, iterations);
  const plaintext = data instanceof Uint8Array ? data : new Uint8Array(data);
  const sealed = new Uint8Array(
    await subtle().encrypt(
      { name: "AES-GCM", iv: iv as BufferSource, additionalData: header as BufferSource },
      key,
      plaintext as BufferSource,
    ),
  );
  const out = new Uint8Array(header.length + sealed.length);
  out.set(header, 0);
  out.set(sealed, header.length);
  return out;
}

export async function decryptPackage(file: ArrayBuffer | Uint8Array, password: string): Promise<Uint8Array> {
  const bytes = file instanceof Uint8Array ? file : new Uint8Array(file);
  if (bytes.length < HEADER_BYTES + GCM_TAG_BYTES || !MAGIC.every((b, i) => bytes[i] === b)) {
    throw new PackageCryptoError("This is not an ArogyaRakshak protected file.");
  }
  if (bytes[MAGIC.length] !== VERSION) {
    throw new PackageCryptoError("This file was made by an unsupported version.");
  }
  const iterations = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength).getUint32(ITER_OFFSET, false);
  if (iterations < 1 || iterations > MAX_ITERATIONS) {
    throw new PackageCryptoError("This file has invalid protection settings.");
  }
  const header = bytes.slice(0, HEADER_BYTES);
  const salt = bytes.slice(SALT_OFFSET, SALT_OFFSET + SALT_BYTES);
  const iv = bytes.slice(IV_OFFSET, HEADER_BYTES);
  const key = await deriveKey(password, salt, iterations);
  try {
    return new Uint8Array(
      await subtle().decrypt(
        { name: "AES-GCM", iv: iv as BufferSource, additionalData: header as BufferSource },
        key,
        bytes.slice(HEADER_BYTES) as BufferSource,
      ),
    );
  } catch {
    // AES-GCM cannot tell a wrong password from a damaged file; say both.
    throw new PackageCryptoError("Wrong password, or the file has been changed or damaged.");
  }
}
