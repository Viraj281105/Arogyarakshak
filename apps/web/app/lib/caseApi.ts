// Case lifecycle calls shared by the case desk and the case workspace. Every call goes through
// apiFetch (the session cookie); no credential is ever placed in a URL.
import { accountPaths, type OwnedCaseSummary } from "../shared/api-client";
import { API_BASE } from "./apiBase";
import { apiErrorMessage, apiFetch } from "./apiFetch";
import { caseHeaders, type CaseRef } from "./caseStore";
import { saveBlob } from "./download";

const K = "/api/v1/kadi";
export const casePath = (id: string) => `${K}/cases/${encodeURIComponent(id)}`;

export class CaseApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function failed(res: Response): Promise<CaseApiError> {
  return new CaseApiError(await apiErrorMessage(res), res.status);
}

/** Creates a case owned by the signed-in account (ADR-029). No case token exists. */
export async function createCase(consentOptIn: boolean): Promise<CaseRef> {
  const res = await apiFetch(`${K}/cases`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ consent_opt_in: consentOptIn }),
  });
  if (!res.ok) throw await failed(res);
  const body = (await res.json()) as { id: string };
  return { id: body.id, token: null, owned: true };
}

export async function uploadDocument(ref: CaseRef, file: File): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  const res = await apiFetch(`${casePath(ref.id)}/upload`, { method: "POST", headers: caseHeaders(ref), body: form });
  if (!res.ok) throw await failed(res);
}

/** DELETE /cases/{id}: the real erasure (P1-10). 404 counts as done (already purged). */
export async function deleteCase(ref: CaseRef): Promise<void> {
  const res = await apiFetch(casePath(ref.id), { method: "DELETE", headers: caseHeaders(ref) });
  if (!res.ok && res.status !== 204 && res.status !== 404) throw await failed(res);
}

/** Signed-in: the account's live cases (never a token). */
export async function listOwnedCases(): Promise<OwnedCaseSummary[]> {
  const res = await apiFetch(accountPaths.cases, { headers: { Accept: "application/json" } });
  if (!res.ok) throw await failed(res);
  return ((await res.json()) as { cases: OwnedCaseSummary[] }).cases;
}

/** Moves a guest case into the signed-in account: presents its token once; afterwards it stops working. */
export async function claimCase(id: string, token: string): Promise<{ claimed: boolean }> {
  const res = await apiFetch(accountPaths.claim(id), { method: "POST", headers: { "X-Case-Access-Token": token } });
  if (!res.ok) throw await failed(res);
  return (await res.json()) as { claimed: boolean };
}

export interface CaseSummary {
  id: string;
  status: string;
  consent_opt_in: boolean;
  total_charged: number;
  created_at: string | null;
}

export interface CaseEntity {
  id: string;
  name: string;
  type: string;
  value: string | null;
  meta: Record<string, unknown> | null;
}

export async function fetchCaseDetail(ref: CaseRef): Promise<{ case: CaseSummary; entities: CaseEntity[] }> {
  const res = await apiFetch(casePath(ref.id), { headers: caseHeaders(ref) });
  if (!res.ok) throw await failed(res);
  return (await res.json()) as { case: CaseSummary; entities: CaseEntity[] };
}

/** GET a case-scoped JSON route (insights, timeline, graph, appeal verify, ...). */
export async function getCaseJson<T>(ref: CaseRef, path: string): Promise<T> {
  const res = await apiFetch(path, { headers: { Accept: "application/json", ...caseHeaders(ref) } });
  if (!res.ok) throw await failed(res);
  return (await res.json()) as T;
}

/**
 * The processing stream (SSE). `withCredentials` carries the session cookie (ADR-026); nothing
 * in the URL authorizes anything, and a session token is never put in one.
 */
export function openCaseStream(ref: CaseRef): EventSource {
  return new EventSource(`${API_BASE}${casePath(ref.id)}/stream`, { withCredentials: true });
}

/**
 * Downloads a case file (appeal PDF, claim PDF, claim package) as bytes, with the case token
 * header or the session cookie, then hands the blob to the browser. Never builds a link that
 * carries a credential.
 */
export async function downloadCaseFile(ref: CaseRef, path: string, filename: string): Promise<void> {
  const res = await apiFetch(path, { headers: caseHeaders(ref) });
  if (!res.ok) throw await failed(res);
  saveBlob(await res.blob(), filename);
}
