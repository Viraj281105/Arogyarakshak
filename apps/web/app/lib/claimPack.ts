// Claim Pack download (ADR-015): fetch the case's pack ZIP and, only if the person opted in,
// seal it in the browser with packageCrypto (ADR-014). The password is used locally and is
// never sent anywhere; the request carries only the per-case access token (ADR-009).

import { ENCRYPTED_EXTENSION, encryptPackage } from "./packageCrypto";

export interface ClaimPackFile {
  bytes: Uint8Array;
  filename: string;
  mimeType: string;
}

export class ClaimPackError extends Error {}

export function claimPackPath(caseId: string): string {
  return `/api/v1/kadi/cases/${encodeURIComponent(caseId)}/claim-pack`;
}

export async function fetchClaimPack(
  apiBase: string,
  caseId: string,
  caseToken: string | undefined,
  options: { password?: string; fetchImpl?: typeof fetch; iterations?: number } = {},
): Promise<ClaimPackFile> {
  const doFetch = options.fetchImpl ?? fetch;
  const headers: Record<string, string> = caseToken ? { "X-Case-Access-Token": caseToken } : {};
  const res = await doFetch(`${apiBase}${claimPackPath(caseId)}`, { headers });
  if (!res.ok) {
    let message = `Could not build the Claim Pack (HTTP ${res.status}).`;
    try {
      const body = await res.json();
      if (typeof body?.message === "string" && body.message) message = body.message;
      else if (typeof body?.detail === "string" && body.detail) message = body.detail;
    } catch {
      /* keep the generic message */
    }
    throw new ClaimPackError(message);
  }
  const plain = new Uint8Array(await res.arrayBuffer());
  const filename = `claim_pack_${caseId}.zip`;
  if (!options.password) return { bytes: plain, filename, mimeType: "application/zip" };
  const sealed = await encryptPackage(plain, options.password, options.iterations);
  return { bytes: sealed, filename: `${filename}${ENCRYPTED_EXTENSION}`, mimeType: "application/octet-stream" };
}
