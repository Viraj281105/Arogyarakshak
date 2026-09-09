"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";

interface SchemeSetuViewProps {
  currentLang: Language;
}

export const SchemeSetuView: React.FC<SchemeSetuViewProps> = ({ currentLang }) => {
  const t = translations[currentLang].modules.schemesetu;

  const [income, setIncome] = useState("120000");
  const [state, setState] = useState("Maharashtra");
  const [medicalNeed, setMedicalNeed] = useState("Heart bypass surgery (CABG)");
  const [hasChecked, setHasChecked] = useState(true);

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
        <div className="grid-3" style={{ marginBottom: "1.25rem" }}>
          <div>
            <label className="input-label">{t.annualIncome}</label>
            <input
              type="number"
              className="input-field"
              value={income}
              onChange={(e) => setIncome(e.target.value)}
            />
          </div>
          <div>
            <label className="input-label">{t.state}</label>
            <select
              className="select-field"
              value={state}
              onChange={(e) => setState(e.target.value)}
            >
              <option value="Maharashtra">Maharashtra</option>
              <option value="Delhi">Delhi</option>
              <option value="Karnataka">Karnataka</option>
              <option value="Uttar Pradesh">Uttar Pradesh</option>
              <option value="Gujarat">Gujarat</option>
              <option value="Tamil Nadu">Tamil Nadu</option>
            </select>
          </div>
          <div>
            <label className="input-label">{t.medicalNeed}</label>
            <input
              type="text"
              className="input-field"
              value={medicalNeed}
              onChange={(e) => setMedicalNeed(e.target.value)}
            />
          </div>
        </div>

        <button
          type="button"
          className="btn btn-primary"
          style={{ width: "100%" }}
          onClick={() => setHasChecked(true)}
        >
          🔍 {t.checkBtn}
        </button>
      </div>

      {hasChecked && (
        <div>
          <h3 style={{ marginBottom: "1rem" }}>{t.eligibleSchemes}</h3>

          <div className="grid-2">
            {/* PM-JAY Card */}
            <div
              style={{
                background: "var(--bg-base)",
                padding: "1.25rem",
                borderRadius: "var(--radius-md)",
                border: "1px solid rgba(6, 182, 212, 0.3)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <strong style={{ color: "var(--brand-cyan)", fontSize: "1.05rem" }}>
                  Ayushman Bharat PM-JAY
                </strong>
                <span className="badge badge-success">98% Match</span>
              </div>
              <p style={{ fontSize: "0.85rem", marginBottom: "0.75rem" }}>
                National flagship cashless secondary and tertiary hospitalization cover.
              </p>
              <div style={{ fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                <div>
                  <span style={{ color: "var(--text-secondary)" }}>{t.maxCoverage}:</span>{" "}
                  <strong>₹5,00,000 / family / year</strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-secondary)" }}>Empanelled Network:</span>{" "}
                  <strong>27,000+ Public & Private Hospitals</strong>
                </div>
              </div>
            </div>

            {/* State Scheme Card (MJPJAY for Maharashtra) */}
            {state === "Maharashtra" && (
              <div
                style={{
                  background: "var(--bg-base)",
                  padding: "1.25rem",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid rgba(16, 185, 129, 0.3)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                  <strong style={{ color: "var(--brand-emerald)", fontSize: "1.05rem" }}>
                    {t.mjpjayCard}
                  </strong>
                  <span className="badge badge-success">State Scheme</span>
                </div>
                <p style={{ fontSize: "0.85rem", marginBottom: "0.75rem" }}>
                  Universal coverage for Maharashtra residents covering 1,356 medical/surgical procedures.
                </p>
                <div style={{ fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                  <div>
                    <span style={{ color: "var(--text-secondary)" }}>{t.maxCoverage}:</span>{" "}
                    <strong>₹5,00,000 / family / year</strong>
                  </div>
                  <div>
                    <span style={{ color: "var(--text-secondary)" }}>Verification:</span>{" "}
                    <strong>Ration Card (Yellow/Orange/White) + Aadhaar</strong>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
