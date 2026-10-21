"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";
import { useApi, API_BASE, caseAuthHeaders } from "../../hooks/useApi";
import { PreauthReadinessPanel } from "../clinical/PreauthReadinessPanel";
import { StatePanel } from "../clinical/StatePanel";
import { saveBlob } from "../../lib/download";
import {
  ENCRYPTED_EXTENSION,
  PackageCryptoError,
  decryptPackage,
  encryptPackage,
  passwordProblem,
} from "../../lib/packageCrypto";

// --- API Response Type (matching backend ClaimPackage schema) ---
interface ClaimFormData {
  policy_number: string;
  patient_name: string;
  hospital_name: string;
  diagnosis: string;
  estimated_cost: number;
  treatment_plan: string;
}

interface ClaimPackageResponse {
  claim_id: string;
  form_data: ClaimFormData;
  form_filled_pdf_path: string | null;
  status: string;
}

interface DaaviSetuViewProps {
  currentLang: Language;
  caseId?: string;
  caseToken?: string;
}

export const DaaviSetuView: React.FC<DaaviSetuViewProps> = ({ currentLang, caseId, caseToken }) => {
  const t = translations[currentLang].modules.daavisetu;
  const api = useApi<ClaimPackageResponse>();

  // Deliberately empty. Pre-filling produced a persisted pre-authorization form for a
  // fabricated patient and policy whenever the user submitted without editing.
  const [patientName, setPatientName] = useState("");
  const [policyId, setPolicyId] = useState("");
  const [hospital, setHospital] = useState("");
  const [treatment, setTreatment] = useState("");
  const [diagnosis, setDiagnosis] = useState("");
  // Optional: the API falls back to the case's bill total and refuses (422) when neither exists.
  const [estimatedCost, setEstimatedCost] = useState("");
  const [copied, setCopied] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  // #101 — optional client-side password protection. The password never leaves the browser.
  const [protect, setProtect] = useState(false);
  const [protectPassword, setProtectPassword] = useState("");
  const [protectConfirm, setProtectConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [unlockPassword, setUnlockPassword] = useState("");
  const [unlockMessage, setUnlockMessage] = useState<string | null>(null);

  const saveBytes = (bytes: BlobPart, filename: string, type: string) => saveBlob(new Blob([bytes], { type }), filename);

  const protectionProblem = protect
    ? passwordProblem(protectPassword) ?? (protectPassword !== protectConfirm ? "The two passwords do not match." : null)
    : null;

  const handleUnlock = async (file: File | undefined) => {
    setUnlockMessage(null);
    if (!file) return;
    if (!unlockPassword) {
      setUnlockMessage("Enter the password first, then choose the file.");
      return;
    }
    try {
      const plain = await decryptPackage(await file.arrayBuffer(), unlockPassword);
      const original = file.name.endsWith(ENCRYPTED_EXTENSION) ? file.name.slice(0, -ENCRYPTED_EXTENSION.length) : `${file.name}.decrypted`;
      saveBytes(plain as BlobPart, original, "application/octet-stream");
      setUnlockMessage("Unlocked on this device. Nothing was sent anywhere.");
    } catch (e) {
      setUnlockMessage(e instanceof PackageCryptoError ? e.message : "Could not unlock the file.");
    }
  };

  const handleGenerate = async () => {
    if (!caseId) return;
    if (!patientName.trim() || !policyId.trim()) return;
    const cost = Number(estimatedCost);
    await api.execute(`/api/v1/daavisetu/cases/${caseId}/claim`, {
      headers: caseAuthHeaders(caseToken),
      body: {
        policy_number: policyId.trim(),
        patient_name: patientName.trim(),
        // Blank optional fields are omitted so the API can fall back to entities
        // extracted from the uploaded document rather than storing an empty string.
        ...(hospital.trim() ? { hospital_name: hospital.trim() } : {}),
        ...(treatment.trim() ? { treatment_plan: treatment.trim() } : {}),
        ...(diagnosis.trim() ? { diagnosis: diagnosis.trim() } : {}),
        ...(estimatedCost.trim() && Number.isFinite(cost) && cost >= 0 ? { estimated_cost: cost } : {}),
      },
    });
  };

  const downloadBlob = async (path: string, filename: string, notFoundLabel: string) => {
    if (!caseId) return;
    setDownloadError(null);
    if (protect && protectionProblem) {
      setDownloadError(protectionProblem);
      return;
    }
    try {
      // A plain <a href> cannot carry the X-Case-Access-Token header (ADR-009), so the
      // file is fetched here and handed to the browser as a blob download instead.
      const res = await fetch(`${API_BASE}${path}`, {
        headers: caseAuthHeaders(caseToken),
      });
      if (!res.ok) {
        setDownloadError(`Could not download the ${notFoundLabel} (HTTP ${res.status}).`);
        return;
      }
      const blob = await res.blob();
      if (protect) {
        const problem = protectionProblem;
        if (problem) {
          setDownloadError(problem);
          return;
        }
        setBusy(true);
        const sealed = await encryptPackage(await blob.arrayBuffer(), protectPassword);
        saveBytes(sealed as BlobPart, `${filename}${ENCRYPTED_EXTENSION}`, "application/octet-stream");
      } else {
        saveBytes(blob, filename, blob.type);
      }
    } catch {
      setDownloadError(`Could not download the ${notFoundLabel}. Is the backend reachable?`);
    } finally {
      setBusy(false);
    }
  };

  const handleDownloadPdf = () =>
    downloadBlob(`/api/v1/daavisetu/cases/${caseId}/claim/pdf`, `preauth_${caseId}.pdf`, "PDF");

  // #81 — ZIP package: the pre-auth PDF, a redacted case-summary excerpt (when Kadi
  // extracted one), and a manifest disclosing exactly what is and is not included.
  const handleDownloadPackage = () =>
    downloadBlob(`/api/v1/daavisetu/cases/${caseId}/claim/package`, `claim_package_${caseId}.zip`, "claim package");

  const result = api.data;
  const canGenerate = !!caseId && !!patientName.trim() && !!policyId.trim();

  const copySummary = async () => {
    if (!result) return;
    const packageSummary = [
      `Pre-Authorization Package: ${result.claim_id}`,
      `Patient: ${result.form_data.patient_name}`,
      `Policy: ${result.form_data.policy_number}`,
      `Hospital: ${result.form_data.hospital_name}`,
      `Diagnosis: ${result.form_data.diagnosis}`,
      `Treatment: ${result.form_data.treatment_plan}`,
      `Estimated Cost: ₹${result.form_data.estimated_cost.toLocaleString("en-IN")}`,
    ].join("\n");
    try {
      await navigator.clipboard.writeText(packageSummary);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setDownloadError("Could not copy to the clipboard.");
    }
  };

  const field = (
    id: string,
    label: string,
    value: string,
    set: (v: string) => void,
    opts: { placeholder?: string; required?: boolean; number?: boolean } = {}
  ) => (
    <div className="ds-field">
      <label className="input-label" htmlFor={id}>
        {label}
        <span className={opts.required ? "ds-required" : "ds-optional"}>{opts.required ? "required" : "optional"}</span>
      </label>
      <input
        id={id}
        type={opts.number ? "number" : "text"}
        inputMode={opts.number ? "decimal" : undefined}
        min={opts.number ? 0 : undefined}
        className="input-field"
        placeholder={opts.placeholder}
        value={value}
        required={opts.required}
        onChange={(e) => set(e.target.value)}
      />
    </div>
  );

  return (
    <div className="module-panel">
      <header className="module-head">
        <p className="lp-kicker">DaaviSetu · cashless pre-authorisation</p>
        <h2>{t.title}</h2>
        <p>{t.desc}</p>
      </header>

      {!caseId && (
        <div className="module-empty">
          <span className="module-empty-icon" aria-hidden="true">
            <svg width="26" height="26" viewBox="0 0 24 24" className="lp-icon">
              <path d="M8 4h8v3H8zM6 6H5v15h14V6h-1M9 12h6M9 16h4" />
            </svg>
          </span>
          <div>
            <strong>No document checked yet</strong>
            <p>
              Upload a hospital document first to create a case. DaaviSetu then checks which commonly requested documents it
              can find, and fills the pre-authorisation form from what you type and what the document says.
            </p>
            <a href="#intake-dropzone" className="btn btn-secondary btn-compact">
              Add a document
            </a>
          </div>
        </div>
      )}

      <ol className="ds-steps">
        {/* ADR-011: documentation completeness + clinician fact confirmation (no approval claims) */}
        {caseId && (
          <li className="ds-step">
            <span className="ds-step-num" aria-hidden="true">1</span>
            <div className="ds-step-body">
              <PreauthReadinessPanel caseId={caseId} caseToken={caseToken} lang={currentLang} />
            </div>
          </li>
        )}

        <li className={`ds-step ${caseId ? "" : "is-disabled"}`}>
          <span className="ds-step-num" aria-hidden="true">{caseId ? 2 : 1}</span>
          <div className="ds-step-body">
            <section className="case-panel bn-card" aria-labelledby="ds-form-title">
              <h3 id="ds-form-title">Fill the pre-authorisation form</h3>
              <p className="bn-fine">
                Name and policy number come from you. Hospital, treatment, diagnosis and cost are taken from your document
                when left blank; if the document does not say, no form is made and you are told what is missing.
              </p>
              <div className="ds-grid">
                {field("ds-patient", t.patientName, patientName, setPatientName, { placeholder: t.patientNamePlaceholder, required: true })}
                {field("ds-policy", t.policyId, policyId, setPolicyId, { placeholder: t.policyIdPlaceholder, required: true })}
                {field("ds-hospital", t.hospital, hospital, setHospital, { placeholder: t.optionalFromDocument })}
                {field("ds-treatment", t.treatment, treatment, setTreatment, { placeholder: t.optionalFromDocument })}
                {field("ds-diagnosis", t.diagnosis, diagnosis, setDiagnosis, { placeholder: t.optionalFromDocument })}
                {field("ds-cost", "Estimated cost (₹)", estimatedCost, setEstimatedCost, {
                  number: true,
                  placeholder: "Leave blank to use the bill total",
                })}
              </div>
              <div className="ds-form-actions">
                <button type="button" className="btn btn-primary" onClick={handleGenerate} disabled={api.loading || !canGenerate}>
                  {api.loading ? (
                    <>
                      <span className="spinner" aria-hidden="true" />
                      Filling the form…
                    </>
                  ) : (
                    t.generateBtn
                  )}
                </button>
                <span className="ds-hint">
                  {!caseId
                    ? "Available once a document has been read."
                    : !canGenerate
                      ? "Enter the patient's name and policy number to continue."
                      : null}
                </span>
              </div>
              {api.error && (
                <StatePanel kind="error" onRetry={handleGenerate}>
                  Could not fill the form: {api.error}
                </StatePanel>
              )}
            </section>
          </div>
        </li>

        {result && (
          <li className="ds-step">
            <span className="ds-step-num is-done" aria-hidden="true">
              <svg width="14" height="14" viewBox="0 0 24 24" className="lp-icon">
                <path d="M5 12.5l4.2 4.2L19 7" />
              </svg>
            </span>
            <div className="ds-step-body">
              <section className="case-panel bn-card ds-result" aria-labelledby="ds-result-title">
                <div className="case-panel-head">
                  <h3 id="ds-result-title">{t.preAuthSummary}</h3>
                  <span className="bn-badges">
                    <span className="badge badge-info" title="Laid out after the IRDAI Annexure-B pre-authorisation form">
                      Annexure-B layout
                    </span>
                    <span className="badge badge-demo code-tabular">{result.claim_id}</span>
                  </span>
                </div>

                <dl className="ds-summary">
                  <div>
                    <dt>Patient</dt>
                    <dd>{result.form_data.patient_name}</dd>
                  </div>
                  <div>
                    <dt>Policy number</dt>
                    <dd className="code-tabular">{result.form_data.policy_number}</dd>
                  </div>
                  <div>
                    <dt>Hospital</dt>
                    <dd>{result.form_data.hospital_name}</dd>
                  </div>
                  <div>
                    <dt>Treatment plan</dt>
                    <dd>{result.form_data.treatment_plan}</dd>
                  </div>
                  <div>
                    <dt>Diagnosis</dt>
                    <dd>{result.form_data.diagnosis}</dd>
                  </div>
                  <div>
                    <dt>Estimated cost</dt>
                    <dd className="code-tabular">₹{result.form_data.estimated_cost.toLocaleString("en-IN")}</dd>
                  </div>
                </dl>

                <p className={`ds-status ${result.status === "ready_for_review" ? "is-ready" : ""}`}>
                  {result.status === "ready_for_review"
                    ? "Ready for you to review — check every field before the hospital desk sends it to the insurer."
                    : `Status: ${result.status}`}
                </p>

                <div className="bn-actions-row">
                  <button type="button" onClick={handleDownloadPdf} className="btn btn-primary" disabled={busy}>
                    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
                      <path d="M12 4v11M7 10l5 5 5-5M5 20h14" />
                    </svg>
                    Download pre-authorisation PDF
                  </button>
                  <button type="button" onClick={handleDownloadPackage} className="btn btn-secondary" disabled={busy}>
                    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
                      <path d="M4 7h16v13H4zM9 7V4h6v3M4 12h16" />
                    </svg>
                    Download claim package (ZIP)
                  </button>
                  <button type="button" className="btn btn-ghost" onClick={() => void copySummary()}>
                    {copied ? "Copied" : "Copy summary"}
                  </button>
                </div>

                <label className="consent-wrapper ds-protect">
                  <input type="checkbox" className="consent-checkbox" checked={protect} onChange={(e) => setProtect(e.target.checked)} />
                  <span>Protect downloads with a password (encrypted on this device)</span>
                </label>
                {protect && (
                  <div className="claim-pack-password">
                    <div className="grid-2">
                      <input type="password" className="input-field" autoComplete="new-password" placeholder="Password (8+ characters)" aria-label="Download password" value={protectPassword} onChange={(e) => setProtectPassword(e.target.value)} />
                      <input type="password" className="input-field" autoComplete="new-password" placeholder="Repeat password" aria-label="Repeat download password" value={protectConfirm} onChange={(e) => setProtectConfirm(e.target.value)} />
                    </div>
                    <p className="claim-pack-note">
                      The password is never sent to our servers and cannot be recovered. If you forget it, the file cannot be
                      opened. The downloaded file ends in {ENCRYPTED_EXTENSION}; open it with &ldquo;Unlock a protected
                      file&rdquo; below.
                      {busy ? " Encrypting…" : ""}
                    </p>
                  </div>
                )}
                <details className="ds-unlock">
                  <summary>Unlock a protected file</summary>
                  <div className="grid-2">
                    <input type="password" className="input-field" autoComplete="off" placeholder="Password" aria-label="Unlock password" value={unlockPassword} onChange={(e) => setUnlockPassword(e.target.value)} />
                    <input type="file" className="input-field" accept={ENCRYPTED_EXTENSION} aria-label="Protected file" onChange={(e) => { void handleUnlock(e.target.files?.[0]); e.target.value = ""; }} />
                  </div>
                  {unlockMessage && <p className="claim-pack-note">{unlockMessage}</p>}
                </details>
                {downloadError && <StatePanel kind="error">{downloadError}</StatePanel>}
              </section>
            </div>
          </li>
        )}
      </ol>
    </div>
  );
};
