"use client";

import React, { useRef, useState } from "react";
import { Language, translations } from "../translations";

interface DocumentUploaderProps {
  currentLang: Language;
  onStartAudit: (fileName: string) => void;
  isProcessing: boolean;
}

export const DocumentUploader: React.FC<DocumentUploaderProps> = ({
  currentLang,
  onStartAudit,
  isProcessing,
}) => {
  const t = translations[currentLang];
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [consentGiven, setConsentGiven] = useState<boolean>(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleTriggerBrowse = () => {
    fileInputRef.current?.click();
  };

  const handleTriggerCamera = () => {
    cameraInputRef.current?.click();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!consentGiven) return;
    const name = selectedFile ? selectedFile.name : "sample_hospital_bill.pdf";
    onStartAudit(name);
  };

  return (
    <div className="card card-glass" style={{ marginBottom: "2rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" }}>
        <div>
          <h2>{t.upload.title}</h2>
          <p>{t.upload.subtitle}</p>
        </div>
        <span className="privacy-pill">
          🔒 {t.byodBadge}
        </span>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Hidden inputs for File and Camera */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept="image/*,application/pdf"
          style={{ display: "none" }}
          id="file-upload-input"
          aria-label="Upload document file"
        />
        <input
          type="file"
          ref={cameraInputRef}
          onChange={handleFileChange}
          accept="image/*"
          capture="environment"
          style={{ display: "none" }}
          id="camera-capture-input"
          aria-label="Snap photo with camera"
        />

        <div
          className="dropzone"
          onClick={handleTriggerBrowse}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              handleTriggerBrowse();
            }
          }}
          aria-label="Document upload dropzone"
        >
          <svg
            width="40"
            height="40"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ color: "var(--brand-cyan)", margin: "0 auto 0.75rem auto" }}
            aria-hidden="true"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>

          <p style={{ fontWeight: 600, color: "var(--text-primary)" }}>
            {selectedFile ? (
              <span style={{ color: "var(--brand-teal)" }}>Selected: {selectedFile.name}</span>
            ) : (
              t.upload.dragDrop
            )}
          </p>
          <p style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
            Supports PDF, JPG, PNG (Hospital bills, IRDAI rejection letters, discharge summaries)
          </p>

          <div className="dropzone-actions" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleTriggerBrowse}
            >
              📁 {t.upload.browse}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleTriggerCamera}
            >
              📷 {t.upload.cameraCapture}
            </button>
          </div>
        </div>

        <div style={{ marginTop: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <input
            type="checkbox"
            id="consent-checkbox"
            checked={consentGiven}
            onChange={(e) => setConsentGiven(e.target.checked)}
            style={{ width: "18px", height: "18px", accentColor: "var(--brand-cyan)" }}
          />
          <label htmlFor="consent-checkbox" style={{ fontSize: "0.85rem", color: "var(--text-secondary)", cursor: "pointer" }}>
            {t.upload.consentText}
          </label>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem", marginTop: "1.25rem" }}>
          <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
            ℹ️ {t.upload.zeroRetentionNotice}
          </span>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={!consentGiven || isProcessing}
          >
            {isProcessing ? (
              <>
                <span className="step-indicator active" style={{ display: "inline-block", marginRight: "0.25rem" }} />
                {t.upload.processing}
              </>
            ) : (
              <>⚡ {t.upload.processBtn}</>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
