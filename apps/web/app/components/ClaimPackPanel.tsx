"use client";

import React, { useState } from "react";
import { API_BASE } from "../hooks/useApi";
import { ClaimPackError, fetchClaimPack } from "../lib/claimPack";
import { ENCRYPTED_EXTENSION, passwordProblem } from "../lib/packageCrypto";
import { saveBlob } from "../lib/download";

/**
 * Claim Pack (ADR-015): one ZIP for the person helping with the paperwork. Optional
 * password protection reuses the browser-only encryption from ADR-014.
 */
export const ClaimPackPanel: React.FC<{ caseId: string; caseToken?: string }> = ({ caseId, caseToken }) => {
  const [protect, setProtect] = useState(false);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const problem = protect ? passwordProblem(password) ?? (password !== confirm ? "The two passwords do not match." : null) : null;

  const download = async () => {
    setError(null);
    if (problem) {
      setError(problem);
      return;
    }
    setBusy(true);
    try {
      const file = await fetchClaimPack(API_BASE, caseId, caseToken, { password: protect ? password : undefined });
      saveBlob(new Blob([file.bytes as BlobPart], { type: file.mimeType }), file.filename);
    } catch (e) {
      setError(e instanceof ClaimPackError ? e.message : "Could not build the Claim Pack. Is the backend reachable?");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="glass-panel" style={{ padding: "1rem", marginTop: "1rem" }} aria-label="Claim Pack">
      <h3 style={{ margin: 0 }}>Claim Pack for the person helping you</h3>
      <p style={{ fontSize: "0.9rem", opacity: 0.85 }}>
        One ZIP with a cover sheet, the documentation checklist, insurer deadlines, and any bill audit, appeal draft and
        medicine price check already on this case. Anything missing is marked &ldquo;not available for this case&rdquo;.
        It does not contain your original documents and does not predict approval.
      </p>
      <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.9rem" }}>
        <input type="checkbox" checked={protect} onChange={(e) => setProtect(e.target.checked)} />
        Protect with a password (encrypted on this device)
      </label>
      {protect && (
        <>
          <div className="grid-2" style={{ marginTop: "0.5rem" }}>
            <input type="password" className="input-field" autoComplete="new-password" placeholder="Password (8+ characters)" aria-label="Claim Pack password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <input type="password" className="input-field" autoComplete="new-password" placeholder="Repeat password" aria-label="Repeat Claim Pack password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          </div>
          <p style={{ fontSize: "0.8rem", opacity: 0.8 }}>
            The password never leaves your browser and cannot be recovered. The file ends in {ENCRYPTED_EXTENSION}; share the
            password with your helper separately.
          </p>
        </>
      )}
      <button type="button" className="btn btn-primary" onClick={() => void download()} disabled={busy} style={{ marginTop: "0.75rem" }}>
        {busy ? "Preparing…" : "🗂️ Download Claim Pack (ZIP)"}
      </button>
      {error && <p role="alert" style={{ color: "#ef4444", fontSize: "0.85rem", marginTop: "0.5rem" }}>⚠️ {error}</p>}
    </section>
  );
};
