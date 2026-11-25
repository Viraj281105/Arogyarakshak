"use client";

import React, { useState } from "react";
import { API_BASE } from "../hooks/useApi";
import { ClaimPackError, fetchClaimPack } from "../lib/claimPack";
import { ENCRYPTED_EXTENSION, passwordProblem } from "../lib/packageCrypto";
import { saveBlob } from "../lib/download";
import { StatePanel } from "./clinical/StatePanel";
import { useT } from "../i18n/useT";
import { msg } from "../i18n/format";

// The sections apps/api/app/claim_pack.py can write; each is marked "not available" when absent.
const CONTENTS = [msg("Read-me & manifest"), msg("Documentation checklist"), msg("Deadline timeline"), msg("Bill audit"), msg("Appeal draft"), msg("Medicine price check"), msg("Pre-authorisation form")];

/**
 * Claim Pack (ADR-015): one ZIP for the person helping with the paperwork. Optional
 * password protection reuses the browser-only encryption from ADR-014.
 */
export const ClaimPackPanel: React.FC<{ caseId: string; caseToken?: string }> = ({ caseId, caseToken }) => {
  const tr = useT();
  const [protect, setProtect] = useState(false);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const problem = protect ? passwordProblem(password) ?? (password !== confirm ? tr("The two passwords do not match.") : null) : null;

  const download = async () => {
    setError(null);
    if (problem) {
      setError(tr(problem));
      return;
    }
    setBusy(true);
    try {
      const file = await fetchClaimPack(API_BASE, caseId, caseToken, { password: protect ? password : undefined });
      saveBlob(new Blob([file.bytes as BlobPart], { type: file.mimeType }), file.filename);
    } catch (e) {
      setError(e instanceof ClaimPackError ? tr(e.message, e.vars) : tr("Could not build the Claim Pack. Is the backend reachable?"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="case-panel claim-pack" aria-labelledby="claim-pack-title">
      <div className="claim-pack-intro">
        <span className="claim-pack-icon" aria-hidden="true">
          <svg width="24" height="24" viewBox="0 0 24 24" className="lp-icon">
            <path d="M4 7h16v13H4zM9 7V4h6v3M4 12h16M10 12v2h4v-2" />
          </svg>
        </span>
        <div>
          <h3 id="claim-pack-title">{tr("Claim Pack for the person helping you")}</h3>
          <p>{tr("One ZIP of what is already on this case. Anything missing is marked “not available for this case”. It does not contain your original documents and does not predict approval.")}</p>
        </div>
      </div>
      <ul className="lp-chips claim-pack-contents" aria-label={tr("What the pack can contain")}>
        {CONTENTS.map((c) => (
          <li key={c}>{tr(c)}</li>
        ))}
      </ul>

      <label className="consent-wrapper claim-pack-protect">
        <input type="checkbox" className="consent-checkbox" checked={protect} onChange={(e) => setProtect(e.target.checked)} />
        <span>{tr("Protect with a password (encrypted on this device)")}</span>
      </label>
      {protect && (
        <div className="claim-pack-password">
          <div className="grid-2">
            <input type="password" className="input-field" autoComplete="new-password" placeholder={tr("Password (8+ characters)")} aria-label={tr("Claim Pack password")} value={password} onChange={(e) => setPassword(e.target.value)} />
            <input type="password" className="input-field" autoComplete="new-password" placeholder={tr("Repeat password")} aria-label={tr("Repeat Claim Pack password")} value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          </div>
          <p className="claim-pack-note">{tr("The password never leaves your browser and cannot be recovered. The file ends in {ENCRYPTED_EXTENSION}; share the password with your helper separately.", { ENCRYPTED_EXTENSION: ENCRYPTED_EXTENSION })}</p>
        </div>
      )}
      <div className="claim-pack-actions">
        <button type="button" className="btn btn-primary" onClick={() => void download()} disabled={busy}>
          {busy ? (
            <>
              <span className="spinner" aria-hidden="true" />{tr("Preparing…")}</>
          ) : (
            <>
              <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
                <path d="M12 4v11M7 10l5 5 5-5M5 20h14" />
              </svg>{tr("Download Claim Pack (ZIP)")}</>
          )}
        </button>
      </div>
      {error && <StatePanel kind="error">{error}</StatePanel>}
    </section>
  );
};
