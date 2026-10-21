"use client";

import React, { useRef, useState } from "react";
import { Language, translations } from "../translations";

// Everything the API accepts (ALLOWED_UPLOAD_EXTENSIONS in apps/api/.../kadi.py): scans and
// photos, PDFs, and plain-text/CSV exports. Text files were previously filtered out of the
// picker although the server accepts them, so the synthetic demo documents could not be chosen.
export const DOCUMENT_ACCEPT = "image/*,application/pdf,.pdf,.txt,text/plain,.csv,text/csv";

interface DocumentUploaderProps {
  currentLang: Language;
  onStartAudit: (file: File | null, fileName: string, consentGiven: boolean) => void;
  isProcessing: boolean;
}

export const DocumentUploader: React.FC<DocumentUploaderProps> = ({
  currentLang,
  onStartAudit,
  isProcessing,
}) => {
  const t = translations[currentLang];
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  // Opt-IN: a pre-ticked box is not consent. The value is forwarded to the caller so
  // the case is created with the patient's actual choice, not a hardcoded true.
  const [consentGiven, setConsentGiven] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const [dragging, setDragging] = useState(false);

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) setSelectedFile(file);
  };

  const handleTriggerBrowse = () => {
    fileInputRef.current?.click();
  };

  const handleTriggerCamera = () => {
    cameraInputRef.current?.click();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!consentGiven || !selectedFile) return;
    onStartAudit(selectedFile, selectedFile.name, consentGiven);
  };


  return (
    <section className="intake-card" aria-labelledby="intake-title">
      <div className="intake-head">
        <div>
          <p className="lp-kicker">Start a check</p>
          <h2 id="intake-title">{t.upload.title}</h2>
          <p>{t.upload.subtitle}</p>
        </div>
        <span className="privacy-pill">
          <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
            <rect x="4" y="11" width="16" height="10" rx="2" />
            <path d="M8 11V7a4 4 0 0 1 8 0v4" />
          </svg>
          {t.byodBadge}
        </span>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Hidden inputs for File and Camera */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept={DOCUMENT_ACCEPT}
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
          className={`dropzone ${selectedFile ? "has-file" : ""} ${dragging ? "is-dragging" : ""}`}
          onClick={handleTriggerBrowse}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
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
          <span className="dropzone-icon" aria-hidden="true">
            <svg width="26" height="26" viewBox="0 0 24 24" className="lp-icon">
              {selectedFile ? (
                <path d="M6 3h8l4 4v14H6zM14 3v4h4M9 14l2 2 4-4" />
              ) : (
                <path d="M12 15V4M7 9l5-5 5 5M4 15v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4" />
              )}
            </svg>
          </span>

          <p className="dropzone-title">
            {selectedFile ? (
              <>
                <span className="dropzone-selected-label">Selected</span>
                <span className="dropzone-filename">{selectedFile.name}</span>
              </>
            ) : (
              t.upload.dragDrop
            )}
          </p>
          <p className="dropzone-hint">Hospital bills, discharge summaries, insurer letters or prescriptions</p>

          <ul className="lp-chips dropzone-facts" aria-label="Accepted files">
            <li>PDF · JPG · PNG · TXT · CSV</li>
            <li>Up to 10 MB</li>
            <li>English text recognition for scans</li>
          </ul>

          <div className="dropzone-actions" onClick={(e) => e.stopPropagation()}>
            <button type="button" className="btn btn-secondary" onClick={handleTriggerBrowse}>
              <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
                <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              </svg>
              {t.upload.browse}
            </button>
            <button type="button" className="btn btn-secondary" onClick={handleTriggerCamera}>
              <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
                <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
                <circle cx="12" cy="13" r="3.5" />
              </svg>
              {t.upload.cameraCapture}
            </button>
          </div>
        </div>

        <label htmlFor="consent-checkbox" className="consent-wrapper">
          <input
            type="checkbox"
            id="consent-checkbox"
            className="consent-checkbox"
            checked={consentGiven}
            onChange={(e) => setConsentGiven(e.target.checked)}
          />
          <span>{t.upload.consentText}</span>
        </label>

        <div className="intake-footer">
          <span className="intake-notice">{t.upload.zeroRetentionNotice}</span>
          <button
            type="submit"
            className="btn btn-primary btn-lg"
            disabled={!consentGiven || !selectedFile || isProcessing}
          >
            {isProcessing ? (
              <>
                <span className="spinner" aria-hidden="true" />
                {t.upload.processing}
              </>
            ) : (
              t.upload.processBtn
            )}
          </button>
        </div>
      </form>
    </section>
  );
};
