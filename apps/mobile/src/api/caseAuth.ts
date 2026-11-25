/**
 * Keys of cases created before sign-in was required (ADR-009, ADR-029).
 *
 * A saved key can now do one thing: move its case into the signed-in account
 * (api/session.ts `claimStoredCases`), after which it is deleted. No request is authorised by a
 * case key, and no new key is ever created. Persisted in `expo-secure-store` (SEC-14).
 */

// Loaded lazily via require() (not a static top-level import — same pattern as
// src/config/env.ts's lazy `require('react-native')`) so this module, and everything
// that transitively imports it (client.ts, endpoints.ts), stays importable in the plain
// Node/tsx test environment (apps/mobile/tests/*.test.ts), which has no React Native
// runtime for expo-secure-store's native module to bind to.
type SecureStoreModule = typeof import('expo-secure-store');
async function getSecureStore(): Promise<SecureStoreModule> {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  return require('expo-secure-store') as SecureStoreModule;
}

const caseTokens = new Map<string, string>();

const TOKEN_KEY_PREFIX = 'case_token_';
// SecureStore has no "list all keys" API, so the set of case ids that currently have a
// persisted token is tracked under this one fixed key, mirroring how useOfflineQueue
// tracks its own queue under QUEUE_STORAGE_KEY.
const TOKEN_INDEX_KEY = 'case_token_index';

function tokenStorageKey(caseId: string): string {
  return `${TOKEN_KEY_PREFIX}${caseId}`;
}

async function readIndex(): Promise<string[]> {
  try {
    const SecureStore = await getSecureStore();
    const raw = await SecureStore.getItemAsync(TOKEN_INDEX_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

async function writeIndex(caseIds: string[]): Promise<void> {
  try {
    const SecureStore = await getSecureStore();
    await SecureStore.setItemAsync(TOKEN_INDEX_KEY, JSON.stringify(caseIds));
  } catch (e) {
    console.warn('[caseAuth] Failed to persist case-token index:', e);
  }
}

/** Best-effort background persist — never blocks or throws into the caller. Losing the
 * persisted copy degrades back to pre-SEC-14 behavior (memory-only for this session)
 * rather than breaking the request that is setting the token right now. */
function persistTokenInBackground(caseId: string, token: string): void {
  (async () => {
    try {
      const SecureStore = await getSecureStore();
      await SecureStore.setItemAsync(tokenStorageKey(caseId), token);
      const index = await readIndex();
      if (!index.includes(caseId)) {
        await writeIndex([...index, caseId]);
      }
    } catch (e) {
      console.warn('[caseAuth] Failed to persist case access token:', e);
    }
  })();
}

function clearPersistedTokenInBackground(caseId: string): void {
  (async () => {
    try {
      const SecureStore = await getSecureStore();
      await SecureStore.deleteItemAsync(tokenStorageKey(caseId));
      const index = await readIndex();
      if (index.includes(caseId)) {
        await writeIndex(index.filter((id) => id !== caseId));
      }
    } catch (e) {
      console.warn('[caseAuth] Failed to clear persisted case access token:', e);
    }
  })();
}

export function setCaseAccessToken(caseId: string, token: string): void {
  caseTokens.set(caseId, token);
  persistTokenInBackground(caseId, token);
}

export function getCaseAccessToken(caseId: string): string | undefined {
  return caseTokens.get(caseId);
}

/** SEC-03: called after a successful case deletion so a stale token for a case that no
 * longer exists on the server is never attached to a later request. */
export function clearCaseAccessToken(caseId: string): void {
  caseTokens.delete(caseId);
  clearPersistedTokenInBackground(caseId);
}

/**
 * SEC-14: repopulates the in-memory token Map from SecureStore. Idempotent and safe to
 * call more than once (e.g. once at app start, and again defensively before a queue
 * replay) — never overwrites an in-memory token that is already set with a stale disk
 * copy, since the in-memory value is always at least as fresh.
 */
export async function hydrateCaseAccessTokens(): Promise<void> {
  const caseIds = await readIndex();
  await Promise.all(
    caseIds.map(async (caseId) => {
      if (caseTokens.has(caseId)) return;
      try {
        const SecureStore = await getSecureStore();
        const token = await SecureStore.getItemAsync(tokenStorageKey(caseId));
        if (token) {
          caseTokens.set(caseId, token);
        }
      } catch (e) {
        console.warn(`[caseAuth] Failed to load persisted token for ${caseId}:`, e);
      }
    })
  );
}

/** Every saved (case id, key) pair currently loaded; call `hydrateCaseAccessTokens` first. */
export function storedCaseTokens(): [string, string][] {
  return [...caseTokens.entries()];
}
