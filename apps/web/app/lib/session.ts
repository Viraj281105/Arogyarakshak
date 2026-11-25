// Account session state for the web client (ADR-026). The session itself is an httpOnly
// cookie (`__Host-arogya_session`) the page cannot read; this module only remembers what the
// API last said about it (GET /auth/me) so the header, the case desk and the settings page agree.
// Nothing here is written to storage: a reload asks the API again.
import { accountPaths, isAuthPath, type AccountUser } from "../shared/api-client/accounts";
import { API_BASE } from "./apiBase";

/**
 * - unknown: not asked yet; checking: GET /auth/me in flight
 * - signed-in / signed-out: the API answered
 * - expired: we were signed in and a request came back 401 (idle or absolute timeout, sign-out
 *   in another tab, password changed elsewhere)
 * - unreachable: no answer (API down, or a credentialed request was refused by CORS because the
 *   API's CORS_ORIGINS does not list this site; nobody can sign in then)
 */
export type AccountStatus = "unknown" | "checking" | "signed-in" | "signed-out" | "expired" | "unreachable";

export interface AccountState {
  status: AccountStatus;
  user: AccountUser | null;
}

let state: AccountState = { status: "unknown", user: null };
const listeners = new Set<() => void>();

function setState(next: AccountState): void {
  state = next;
  listeners.forEach((l) => l());
}

export function getAccountState(): AccountState {
  return state;
}

const SERVER_STATE: AccountState = { status: "unknown", user: null };
export function getServerAccountState(): AccountState {
  return SERVER_STATE;
}

export function subscribeAccount(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

let inflight: Promise<AccountState> | null = null;

/** Asks the API who is signed in. Concurrent callers share one request. */
export function refreshAccount(fetchImpl: typeof fetch = fetch): Promise<AccountState> {
  if (inflight) return inflight;
  const before = state.status;
  if (before === "unknown") setState({ status: "checking", user: null });
  inflight = (async () => {
    try {
      const res = await fetchImpl(`${API_BASE}${accountPaths.me}`, {
        credentials: "include",
        headers: { Accept: "application/json" },
      });
      if (res.ok) {
        setState({ status: "signed-in", user: (await res.json()) as AccountUser });
      } else if (res.status === 401) {
        setState({ status: before === "signed-in" ? "expired" : "signed-out", user: null });
      } else {
        setState({ status: "unreachable", user: null });
      }
    } catch {
      setState({ status: "unreachable", user: null });
    } finally {
      inflight = null;
    }
    return state;
  })();
  return inflight;
}

/** Starts the first check if nobody has asked yet (header and pages call this on mount). */
export function ensureAccountChecked(): void {
  if (state.status === "unknown") void refreshAccount();
}

export function markSignedIn(user: AccountUser): void {
  setState({ status: "signed-in", user });
}

export function markSignedOut(): void {
  setState({ status: "signed-out", user: null });
}

/**
 * Called for every 401 from a non-account route. While signed in that means the session ended
 * (expired, revoked, signed out elsewhere); otherwise the state may simply be stale, so ask again.
 */
export function noteUnauthorized(path: string): void {
  if (isAuthPath(path)) return;
  if (state.status === "signed-in") setState({ status: "expired", user: null });
  else if (state.status !== "checking") void refreshAccount();
}

/**
 * Credentials mode for API requests. The cookie must travel ("include") whenever a session may
 * exist. When the API said there is none, or could not be reached, requests go without it
 * ("same-origin"), so the few public requests still get an answer from an API whose
 * CORS_ORIGINS is a wildcard (which refuses every credentialed cross-origin request).
 */
export function requestCredentials(): RequestCredentials {
  return state.status === "signed-out" || state.status === "unreachable" ? "same-origin" : "include";
}

/** Test hook: back to the initial state. */
export function resetAccountStateForTests(): void {
  state = { status: "unknown", user: null };
  inflight = null;
  listeners.clear();
}
