import { normalizeErrorDetail } from "../shared/api-client";
import { API_BASE } from "./apiBase";
import { noteUnauthorized, requestCredentials } from "./session";

/**
 * The one way the web client calls the API: `API_BASE + path`, with the session cookie when a
 * session may exist (session.requestCredentials) and 401s reported to the session state, so an
 * expired session is noticed wherever it happens. Never put a session or case token in `path`.
 */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const res = await fetch(`${API_BASE}${path}`, { credentials: requestCredentials(), ...init });
  if (res.status === 401) noteUnauthorized(path);
  return res;
}

/** The API's error text for a failed response (`detail`, else `message`), or a status line. */
export async function apiErrorMessage(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown; message?: unknown } | null;
    if (body && body.detail !== undefined && body.detail !== null) return normalizeErrorDetail(body.detail);
    if (body && typeof body.message === "string" && body.message) return body.message;
  } catch {
    // not JSON
  }
  return `HTTP ${res.status}`;
}

/** Seconds from a Retry-After header (429), or null. */
export function retryAfterSeconds(res: Response): number | null {
  const raw = res.headers.get("Retry-After");
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) && n >= 0 ? Math.ceil(n) : null;
}
