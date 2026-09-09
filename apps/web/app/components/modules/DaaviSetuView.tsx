"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";

interface DaaviSetuViewProps {
  currentLang: Language;
}

export const DaaviSetuView: React.FC<DaaviSetuViewProps> = ({ currentLang }) => {
  const t = translations[currentLang].modules.daavisetu;

  const [patientName, setPatientName] = useState("Viraj Jadhao");
  const [policyId, setPolicyId] = useState("POL-STAR-774411");
  const [hospital, setHospital] = useState("Apollo Multi-Speciality Hospital, Mumbai");
  const [treatment, setTreatment] = useState("Laparoscopic Appendectomy");
  const [isGenerated, setIsGenerated] = useState(true);

  return (
    <div className="card">
      <div style={{ marginBottom: "1.5rem" }}>
        <h2>{t.title}</h2>
        <p>{t.desc}</p>
      </div>

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
            <input
              type="text"
              className="input-field"
              value={patientName}
              onChange={(e) => setPatientName(e.target.value)}
            />
          </div>
          <div>
            <label className="input-label">{t.policyId}</label>
            <input
              type="text"
              className="input-field"
              value={policyId}
              onChange={(e) => setPolicyId(e.target.value)}
            />
          </div>
        </div>

        <div className="grid-2" style={{ marginBottom: "1.25rem" }}>
          <div>
            <label className="input-label">{t.hospital}</label>
            <input
              type="text"
              className="input-field"
              value={hospital}
              onChange={(e) => setHospital(e.target.value)}
            />
          </div>
          <div>
            <label className="input-label">{t.treatment}</label>
            <input
              type="text"
              className="input-field"
              value={treatment}
              onChange={(e) => setTreatment(e.target.value)}
            />
          </div>
        </div>

        <button
          type="button"
          className="btn btn-primary"
          style={{ width: "100%" }}
          onClick={() => setIsGenerated(true)}
        >
          📄 {t.generateBtn}
        </button>
      </div>

      {isGenerated && (
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
            <span className="badge badge-success">IRDAI Standard Annexure-B</span>
          </div>

          <div className="grid-2" style={{ fontSize: "0.875rem", marginBottom: "1.25rem" }}>
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

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => alert("Pre-authorization package exported as structured PDF/JSON.")}
          >
            📥 {t.downloadPackage}
          </button>
        </div>
      )}
    </div>
  );
};
