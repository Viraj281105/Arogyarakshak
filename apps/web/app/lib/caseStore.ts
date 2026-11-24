// Which cases this browser tab holds, and which one is open (Wave 3 decision D2).
//
// GUEST cases (created without an account) are opened only with their one-time case access token
// (ADR-009). D2 keeps them in `sessionStorage`: per tab, gone when the tab closes, never sent
// anywhere but the API's X-Case-Access-Token header. RISK (accepted in D2, the same one ADR-008
// named for localStorage): any script that runs in this origin (an XSS bug, a malicious browser
// extension) can read sessionStorage and therefore the tokens. Mitigations: tokens are never put in
// a URL, a log or localStorage; the list is capped; signing in and claiming a case moves it to the
// account, after which its token stops working (ADR-026 section 6).
//
// OWNED cases (created or claimed while signed in) have no token: the account's httpOnly cookie
// opens them. Only their id is remembered here, as the "active case".
//
// The active case is held here, NOT in the URL, so a shared or bookmarked link never carries a
// case (architecture doc section 3.2).

export interface GuestCase {
  id: string;
  token: string;
  /** ISO time this tab learnt the case (not a server figure). */
  addedAt: string;
}

export interface ActiveCase {
  id: string;
  owned: boolean;
}

/** What a request for one case needs: its id and, for a guest case, its token. */
export interface CaseRef {
  id: string;
  token: string | null;
  owned: boolean;
}

export const GUEST_CASES_KEY = "arogyarakshak.guestCases.v1";
export const ACTIVE_CASE_KEY = "arogyarakshak.activeCase.v1";
export const MAX_GUEST_CASES = 20;

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

function defaultStorage(): StorageLike | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null; // storage blocked (privacy settings): cases then last until reload only
  }
}

// In-memory fallback so a tab without sessionStorage still works until it reloads.
const memory = new Map<string, string>();
const memoryStorage: StorageLike = {
  getItem: (k) => memory.get(k) ?? null,
  setItem: (k, v) => void memory.set(k, v),
  removeItem: (k) => void memory.delete(k),
};

function store(s?: StorageLike | null): StorageLike {
  return s ?? defaultStorage() ?? memoryStorage;
}

function safeGet(s: StorageLike, key: string): string | null {
  try {
    return s.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(s: StorageLike, key: string, value: string | null): void {
  try {
    if (value === null) s.removeItem(key);
    else s.setItem(key, value);
  } catch {
    // quota or blocked: ignore, the in-memory state still updates listeners
  }
  listeners.forEach((l) => l());
}

const isText = (v: unknown): v is string => typeof v === "string" && v.length > 0 && v.length <= 512;

/** Pure: parse the stored list, dropping anything malformed. */
export function parseGuestCases(raw: string | null): GuestCase[] {
  if (!raw) return [];
  try {
    const list = JSON.parse(raw) as unknown;
    if (!Array.isArray(list)) return [];
    return list
      .filter((c): c is GuestCase => !!c && typeof c === "object" && isText((c as GuestCase).id) && isText((c as GuestCase).token))
      .map((c) => ({ id: c.id, token: c.token, addedAt: typeof c.addedAt === "string" ? c.addedAt : "" }))
      .slice(0, MAX_GUEST_CASES);
  } catch {
    return [];
  }
}

export function parseActiveCase(raw: string | null): ActiveCase | null {
  if (!raw) return null;
  try {
    const v = JSON.parse(raw) as Partial<ActiveCase> | null;
    return v && isText(v.id) ? { id: v.id, owned: v.owned === true } : null;
  } catch {
    return null;
  }
}

export function readGuestCases(s?: StorageLike | null): GuestCase[] {
  return parseGuestCases(safeGet(store(s), GUEST_CASES_KEY));
}

/** Adds (or moves to the front) a guest case; the oldest falls off beyond MAX_GUEST_CASES. */
export function addGuestCase(c: { id: string; token: string }, s?: StorageLike | null, now: Date = new Date()): void {
  const st = store(s);
  const rest = readGuestCases(st).filter((g) => g.id !== c.id);
  const next = [{ id: c.id, token: c.token, addedAt: now.toISOString() }, ...rest].slice(0, MAX_GUEST_CASES);
  safeSet(st, GUEST_CASES_KEY, JSON.stringify(next));
}

export function removeGuestCase(id: string, s?: StorageLike | null): void {
  const st = store(s);
  const next = readGuestCases(st).filter((g) => g.id !== id);
  safeSet(st, GUEST_CASES_KEY, next.length ? JSON.stringify(next) : null);
  if (readActiveCase(st)?.id === id) safeSet(st, ACTIVE_CASE_KEY, null);
}

export function guestToken(id: string, s?: StorageLike | null): string | null {
  return readGuestCases(s).find((g) => g.id === id)?.token ?? null;
}

export function readActiveCase(s?: StorageLike | null): ActiveCase | null {
  return parseActiveCase(safeGet(store(s), ACTIVE_CASE_KEY));
}

export function setActiveCase(c: ActiveCase, s?: StorageLike | null): void {
  safeSet(store(s), ACTIVE_CASE_KEY, JSON.stringify({ id: c.id, owned: c.owned }));
}

export function clearActiveCase(s?: StorageLike | null): void {
  safeSet(store(s), ACTIVE_CASE_KEY, null);
}

/** The active case with its token resolved (guest), or null when none is open or its token is gone. */
export function activeCaseRef(s?: StorageLike | null): CaseRef | null {
  const active = readActiveCase(s);
  if (!active) return null;
  if (active.owned) return { id: active.id, token: null, owned: true };
  const token = guestToken(active.id, s);
  return token ? { id: active.id, token, owned: false } : null;
}

/** Headers for a case-scoped request: the case token for a guest case, nothing for an owned one. */
export function caseHeaders(ref: Pick<CaseRef, "token"> | null | undefined): Record<string, string> {
  return ref?.token ? { "X-Case-Access-Token": ref.token } : {};
}

/** Drops every guest case and the active case (after account deletion or "forget this tab"). */
export function clearAllCases(s?: StorageLike | null): void {
  const st = store(s);
  safeSet(st, GUEST_CASES_KEY, null);
  safeSet(st, ACTIVE_CASE_KEY, null);
}

// --- React subscription (useSyncExternalStore) -----------------------------------------------

const listeners = new Set<() => void>();

export function subscribeCases(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

// Snapshots must be referentially stable between changes.
let guestSnap: { raw: string | null; value: GuestCase[] } = { raw: null, value: [] };
let activeSnap: { key: string; value: CaseRef | null } = { key: "", value: null };

export function guestCasesSnapshot(): GuestCase[] {
  const raw = safeGet(store(), GUEST_CASES_KEY);
  if (raw !== guestSnap.raw) guestSnap = { raw, value: parseGuestCases(raw) };
  return guestSnap.value;
}

export function activeCaseSnapshot(): CaseRef | null {
  const ref = activeCaseRef();
  const key = ref ? `${ref.id}|${ref.owned}|${ref.token ?? ""}` : "";
  if (key !== activeSnap.key) activeSnap = { key, value: ref };
  return activeSnap.value;
}

const EMPTY: GuestCase[] = [];
export const serverGuestCases = (): GuestCase[] => EMPTY;
export const serverActiveCase = (): CaseRef | null => null;
