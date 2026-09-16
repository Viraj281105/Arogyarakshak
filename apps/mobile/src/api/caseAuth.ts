/**
 * Per-case access token store (ADR-009).
 *
 * Every case-scoped route now requires the token returned once by
 * `POST /api/v1/kadi/cases`. Rather than threading it as a prop through every screen
 * that calls a case-scoped endpoint, it is held here — in memory, for this app
 * session only — and `client.ts`'s `request()` attaches it automatically to any
 * request whose URL names a case this store has a token for.
 *
 * This is deliberately NOT persisted to disk: losing it when the app is killed matches
 * the backend's own trade-off (ADR-009) — a case's token exists only for as long as the
 * session that created it, by design, not as an oversight.
 */

const caseTokens = new Map<string, string>();

export function setCaseAccessToken(caseId: string, token: string): void {
  caseTokens.set(caseId, token);
}

export function getCaseAccessToken(caseId: string): string | undefined {
  return caseTokens.get(caseId);
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
