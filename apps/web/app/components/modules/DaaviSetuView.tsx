"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";
import { useApi, API_BASE, caseAuthHeaders } from "../../hooks/useApi";
import { PreauthReadinessPanel } from "../clinical/PreauthReadinessPanel";
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
  const [downloadError, setDownloadError] = useState<string | null>(null);
  // #101 — optional client-side password protection. The password never leaves the browser.
  const [protect, setProtect] = useState(false);
  const [protectPassword, setProtectPassword] = useState("");
  const [protectConfirm, setProtectConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [unlockPassword, setUnlockPassword] = useState("");
  const [unlockMessage, setUnlockMessage] = useState<string | null>(null);

  const saveBytes = (bytes: BlobPart, filename: string, type: string) => {
    const url = URL.createObjectURL(new Blob([bytes], { type }));
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

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

  return (
    <div className="card">
      <div style={{ marginBottom: "1.5rem" }}>
        <h2>{t.title}</h2>
        <p>{t.desc}</p>
      </div>

      {/* ADR-011: documentation completeness + clinician fact confirmation (no approval claims) */}
      {caseId && <PreauthReadinessPanel caseId={caseId} caseToken={caseToken} />}

      {/* Input Form */}
      <div
        style={{
          background: "var(--bg-surface-elevated)",
          padding: "1.25rem",
          borderRadius: "var(--radius-md)",
          border: "1px solid var(--border-subtle)",
          marginBottom: "1.5rem",
        }}
      >
        <div className="grid-2" style={{ marginBottom: "1rem" }}>
          <div>
            <label className="input-label">{t.patientName}</label>
            <input type="text" className="input-field" placeholder={t.patientNamePlaceholder} value={patientName} onChange={(e) => setPatientName(e.target.value)} />
          </div>
          <div>
            <label className="input-label">{t.policyId}</label>
            <input type="text" className="input-field" placeholder={t.policyIdPlaceholder} value={policyId} onChange={(e) => setPolicyId(e.target.value)} />
          </div>
        </div>

        <div className="grid-2" style={{ marginBottom: "1.25rem" }}>
          <div>
            <label className="input-label">{t.hospital}</label>
            <input type="text" className="input-field" placeholder={t.optionalFromDocument} value={hospital} onChange={(e) => setHospital(e.target.value)} />
          </div>
          <div>
            <label className="input-label">{t.treatment}</label>
            <input type="text" className="input-field" placeholder={t.optionalFromDocument} value={treatment} onChange={(e) => setTreatment(e.target.value)} />
          </div>
        </div>

        <div style={{ marginBottom: "1.25rem" }}>
          <label className="input-label">{t.diagnosis}</label>
          <input type="text" className="input-field" placeholder={t.optionalFromDocument} value={diagnosis} onChange={(e) => setDiagnosis(e.target.value)} />
        </div>

        {!caseId && (
          <div
            style={{
              padding: "0.75rem 1rem",
              marginBottom: "1rem",
              background: "rgba(6, 182, 212, 0.06)",
              border: "1px solid rgba(6, 182, 212, 0.2)",
              borderRadius: "var(--radius-md)",
              fontSize: "0.85rem",
              color: "var(--text-secondary)",
            }}
          >
            📤 Upload a hospital document above first to create a case, then generate the pre-authorization package.
          </div>
        )}

        <button
          type="button"
          className="btn btn-primary"
          style={{ width: "100%" }}
          onClick={handleGenerate}
          disabled={api.loading || !caseId || !patientName.trim() || !policyId.trim()}
        >
          {api.loading ? (
            <>
              <span className="step-indicator active" style={{ display: "inline-block", marginRight: "0.25rem" }} />
              Generating pre-authorization package...
            </>
          ) : (
            <>📄 {t.generateBtn}</>
          )}
        </button>
      </div>

      {/* Error State */}
      {api.error && (
        <div
          style={{
            padding: "1rem",
            marginBottom: "1.5rem",
            background: "rgba(239, 68, 68, 0.15)",
            border: "1px solid var(--status-danger)",
            borderRadius: "var(--radius-md)",
            color: "#fca5a5",
            fontSize: "0.9rem",
          }}
        >
          ⚠️ {api.error}
        </div>
      )}

      {/* Real Result */}
      {result && (
        <div
          style={{
            background: "var(--bg-base)",
            padding: "1.25rem",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
            <h3>✓ {t.preAuthSummary}</h3>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              <span className="badge badge-success">IRDAI Standard Annexure-B</span>
              <span className="badge badge-info">{result.claim_id}</span>
            </div>
          </div>

          <div className="grid-2" style={{ fontSize: "0.875rem", marginBottom: "1.25rem" }}>
            <div>
              <span style={{ color: "var(--text-secondary)" }}>Patient:</span>{" "}
              <strong style={{ color: "var(--text-primary)" }}>{result.form_data.patient_name}</strong>
            </div>
            <div>
              <span style={{ color: "var(--text-secondary)" }}>Policy ID:</span>{" "}
              <strong style={{ color: "var(--text-primary)" }}>{result.form_data.policy_number}</strong>
            </div>
            <div>
              <span style={{ color: "var(--text-secondary)" }}>Network Provider:</span>{" "}
              <strong style={{ color: "var(--text-primary)" }}>{result.form_data.hospital_name}</strong>
            </div>
            <div>
              <span style={{ color: "var(--text-secondary)" }}>Clinical Protocol:</span>{" "}
              <strong style={{ color: "var(--text-primary)" }}>{result.form_data.treatment_plan}</strong>
            </div>
            <div>
              <span style={{ color: "var(--text-secondary)" }}>Diagnosis:</span>{" "}
              <strong style={{ color: "var(--text-primary)" }}>{result.form_data.diagnosis}</strong>
            </div>
            <div>
              <span style={{ color: "var(--text-secondary)" }}>Estimated Cost:</span>{" "}
              <strong style={{ color: "var(--text-primary)" }}>₹{result.form_data.estimated_cost.toLocaleString("en-IN")}</strong>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
            <span
              style={{
                fontSize: "0.8rem",
                color: result.status === "ready_for_review" ? "var(--brand-emerald)" : "var(--text-secondary)",
              }}
            >
              Status: {result.status === "ready_for_review" ? "✓ Ready for Review & Submission" : result.status}
            </span>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                const packageSummary = [
                  `Pre-Authorization Package: ${result.claim_id}`,
                  `Patient: ${result.form_data.patient_name}`,
                  `Policy: ${result.form_data.policy_number}`,
                  `Hospital: ${result.form_data.hospital_name}`,
                  `Diagnosis: ${result.form_data.diagnosis}`,
                  `Treatment: ${result.form_data.treatment_plan}`,
                  `Estimated Cost: ₹${result.form_data.estimated_cost.toLocaleString("en-IN")}`,
                ].join("\n");
                navigator.clipboard.writeText(packageSummary);
              }}
            >
              📋 Copy Package Summary
            </button>
            <button
              type="button"
              onClick={handleDownloadPdf}
              className="btn btn-primary"
              style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}
            >
              📥 Download Form VI / Pre-Auth PDF
            </button>
            <button
              type="button"
              onClick={handleDownloadPackage}
              className="btn btn-secondary"
              style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}
            >
              🗂️ Download Full Claim Package (ZIP)
            </button>
          </div>
          <div style={{ marginTop: "1rem" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.9rem" }}>
              <input type="checkbox" checked={protect} onChange={(e) => setProtect(e.target.checked)} />
              Protect downloads with a password (encrypted on this device)
            </label>
            {protect && (
              <div className="grid-2" style={{ marginTop: "0.5rem" }}>
                <input type="password" className="input-field" autoComplete="new-password" placeholder="Password (8+ characters)" aria-label="Download password" value={protectPassword} onChange={(e) => setProtectPassword(e.target.value)} />
                <input type="password" className="input-field" autoComplete="new-password" placeholder="Repeat password" aria-label="Repeat download password" value={protectConfirm} onChange={(e) => setProtectConfirm(e.target.value)} />
              </div>
            )}
            {protect && (
              <p style={{ fontSize: "0.8rem", marginTop: "0.5rem", opacity: 0.8 }}>
                The password is never sent to our servers and cannot be recovered. If you forget it, the file cannot be opened.
                The downloaded file ends in {ENCRYPTED_EXTENSION}; open it with &ldquo;Unlock a protected file&rdquo; below.
                {busy ? " Encrypting…" : ""}
              </p>
            )}
            <details style={{ marginTop: "0.75rem" }}>
              <summary style={{ cursor: "pointer", fontSize: "0.9rem" }}>Unlock a protected file</summary>
              <div className="grid-2" style={{ marginTop: "0.5rem" }}>
                <input type="password" className="input-field" autoComplete="off" placeholder="Password" aria-label="Unlock password" value={unlockPassword} onChange={(e) => setUnlockPassword(e.target.value)} />
                <input type="file" accept={ENCRYPTED_EXTENSION} aria-label="Protected file" onChange={(e) => { void handleUnlock(e.target.files?.[0]); e.target.value = ""; }} />
              </div>
              {unlockMessage && <p style={{ fontSize: "0.85rem", marginTop: "0.5rem" }}>{unlockMessage}</p>}
            </details>
          </div>
          {downloadError && (
            <p style={{ color: "#ef4444", fontSize: "0.85rem", marginTop: "0.5rem" }}>⚠️ {downloadError}</p>
          )}
        </div>
      )}

      {/* Placeholder when no case and no result */}
      {!result && !api.loading && !caseId && (
        <div
          style={{
            background: "var(--bg-base)",
            padding: "1.25rem",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
            opacity: 0.7,
          }}
        >
          <div
            style={{
              padding: "0.5rem 0.75rem",
              marginBottom: "1rem",
              background: "rgba(245, 158, 11, 0.08)",
              borderRadius: "var(--radius-sm, 4px)",
              fontSize: "0.8rem",
              color: "var(--status-warning)",
              fontWeight: 600,
            }}
          >
            ⓘ Nothing generated yet — upload a document first. The fields below are what you have typed, not a
            submitted or approved form.
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
            <h3>{t.preAuthSummary}</h3>
            <span className="badge badge-info">IRDAI Annexure-B format (not generated yet)</span>
          </div>
          <div className="grid-2" style={{ fontSize: "0.875rem" }}>
            <div>
              <span style={{ color: "var(--text-secondary)" }}>Patient:</span>{" "}
              <strong style={{ color: "var(--text-primary)" }}>{patientName}</strong>
            </div>
            <div>
              <span style={{ color: "var(--text-secondary)" }}>Policy ID:</span>{" "}
              <strong style={{ color: "var(--text-primary)" }}>{policyId}</strong>
            </div>
            <div>
              <span style={{ color: "var(--text-secondary)" }}>Network Provider:</span>{" "}
              <strong style={{ color: "var(--text-primary)" }}>{hospital}</strong>
            </div>
            <div>
              <span style={{ color: "var(--text-secondary)" }}>Clinical Protocol:</span>{" "}
              <strong style={{ color: "var(--text-primary)" }}>{treatment}</strong>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
