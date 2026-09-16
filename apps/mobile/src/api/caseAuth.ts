/**
 * Per-case access token store (ADR-009).
 *
 * Every case-scoped route requires the token returned once by
 * `POST /api/v1/kadi/cases`. Rather than threading it as a prop through every screen
 * that calls a case-scoped endpoint, it is held here — in an in-memory Map for fast
 * synchronous lookup by `client.ts`'s `request()` — and mirrored to `expo-secure-store`
 * (SEC-14), the same secure storage mechanism `useOfflineStorage`/`useOfflineQueue`
 * already use for the persisted offline-action queue.
 *
 * Why persistence changed (SEC-14): the offline-action queue is persisted to disk so a
 * pending SUBMIT_PREAUTH/ANALYZE_DENIAL action survives an app restart and replays once
 * back online. Before this fix, the token store here was memory-only ("deliberately not
 * persisted... by design"), so after a restart the queue's actions were still there but
 * every case's token was gone — a replay would attach no token at all, get a 401, and
 * (depending on retry accounting) eventually be silently dropped after MAX_RETRIES
 * attempts that could never have succeeded. Persisting the token alongside the queue
 * that depends on it is what actually delivers "resumes safely after restart" rather
 * than "resumes and then quietly fails."
 *
 * `hydrateCaseAccessTokens()` must be awaited once at app/hook start (see
 * `useOfflineQueue`) to repopulate the in-memory Map from disk before anything tries to
 * replay a queued action — the synchronous Map lookups everywhere else stay unchanged.
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

/** Extracts a case id from a request path like "/api/v1/billnyay/cases/CASE-xxxx/audit". */
export function extractCaseIdFromPath(path: string): string | undefined {
  const match = path.match(/\/cases\/([^/?]+)/);
  return match ? decodeURIComponent(match[1]) : undefined;
}

export function tokenHeaderForPath(path: string): Record<string, string> {
  const caseId = extractCaseIdFromPath(path);
  if (!caseId) return {};
  const token = caseTokens.get(caseId);
  return token ? { 'X-Case-Access-Token': token } : {};
}
