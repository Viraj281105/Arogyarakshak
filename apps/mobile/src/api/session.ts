/**
 * The signed-in account on this device (ADR-026, ADR-029). The API issues a bearer session; it
 * is kept in the device's secure store, sent only in the Authorization header and never put in a
 * URL or a log. Every API route needs it.
 */
import { ENV } from '../config/env';
import { createClient } from '../shared/api-client';
import { accountPaths, isAuthPath, type AccountUser, type SessionResponse } from '../shared/api-client/accounts';
import { readSecure, writeSecure } from '../services/secureValue';
import { clearCaseAccessToken, hydrateCaseAccessTokens, storedCaseTokens } from './caseAuth';
import { tr } from '../translations/tr';

const TOKEN_KEY = 'account_session';

/** loading: reading the secure store; signed-out; expired: the server ended the session. */
export type SessionStatus = 'loading' | 'signed-out' | 'signed-in' | 'expired';

let token: string | null = null;
let status: SessionStatus = 'loading';
const listeners = new Set<() => void>();

function set(next: SessionStatus, nextToken: string | null): void {
  status = next;
  token = nextToken;
  void writeSecure(TOKEN_KEY, nextToken);
  listeners.forEach((l) => l());
}

export function getSessionStatus(): SessionStatus {
  return status;
}

export function subscribeSession(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function sessionHeaders(): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Called for a 401 from any route that is not an account route. */
export function noteUnauthorized(path: string): void {
  if (!isAuthPath(path) && token) set('expired', null);
}

function client() {
  return createClient({ baseUrl: ENV.API_BASE_URL, timeoutMs: ENV.TIMEOUT_MS, headersFor: sessionHeaders });
}

/** Restores a saved session and checks the server still accepts it. */
export async function hydrateSession(): Promise<void> {
  const saved = await readSecure(TOKEN_KEY);
  if (!saved) return set('signed-out', null);
  token = saved;
  try {
    await client().request<AccountUser>(accountPaths.me);
    set('signed-in', saved);
  } catch (err) {
    const code = (err as { statusCode?: number }).statusCode;
    // No answer is not a refusal: keep the session and let requests report the connection.
    if (code === 401) set('expired', null);
    else set('signed-in', saved);
  }
}

/** Moves cases created before sign-in was required into the account, using their saved keys. */
export async function claimStoredCases(): Promise<number> {
  await hydrateCaseAccessTokens();
  let claimed = 0;
  for (const [caseId, caseToken] of storedCaseTokens()) {
    try {
      await client().request(accountPaths.claim(caseId), {
        method: 'POST',
        headers: { 'X-Case-Access-Token': caseToken },
      });
      claimed += 1;
      clearCaseAccessToken(caseId);
    } catch (err) {
      const code = (err as { statusCode?: number }).statusCode;
      // Gone or already owned: the key is of no further use. Anything else: try next time.
      if (code === 403 || code === 404) clearCaseAccessToken(caseId);
    }
  }
  return claimed;
}

export async function signIn(email: string, password: string): Promise<void> {
  const body = await client().request<SessionResponse>(accountPaths.login, {
    method: 'POST',
    body: JSON.stringify({ email: email.trim(), password, session_transport: 'bearer' }),
  });
  if (!body.token) throw new Error(tr('The server did not return a session.'));
  set('signed-in', body.token);
  void claimStoredCases();
}

/** Registration answers the same whether or not the address is taken, so sign in afterwards. */
export async function register(email: string, password: string): Promise<void> {
  await client().request(accountPaths.register, {
    method: 'POST',
    body: JSON.stringify({ email: email.trim(), password }),
  });
}

export async function signOut(): Promise<void> {
  try {
    await client().request(accountPaths.logout, { method: 'POST' });
  } catch {
    // The session still leaves this device; the server expires it.
  }
  set('signed-out', null);
}

export function resetSessionForTests(next: SessionStatus = 'signed-out', nextToken: string | null = null): void {
  status = next;
  token = nextToken;
  listeners.clear();
}
