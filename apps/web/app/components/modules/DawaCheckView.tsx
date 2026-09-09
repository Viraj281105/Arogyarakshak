"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";

interface DawaCheckViewProps {
  currentLang: Language;
}

export const DawaCheckView: React.FC<DawaCheckViewProps> = ({ currentLang }) => {
  const t = translations[currentLang].modules.dawacheck;

  const [query, setQuery] = useState("Paracetamol 650mg");

  const sampleMedicines = [
    {
      brand: "Dolo 650mg Tablet (15s)",
      generic: "Paracetamol 650mg",
      mrp: 33.5,
      nppaCeiling: 28.5,
      isOvercharged: true,
      overcharge: 5.0,
    },
    {
      brand: "Augmentin 625 Duo Tablet (10s)",
      generic: "Amoxicillin (500mg) + Clavulanic Acid (125mg)",
      mrp: 220.0,
      nppaCeiling: 198.4,
      isOvercharged: true,
      overcharge: 21.6,
    },
    {
      brand: "Metformin 500mg SR Tablet (10s)",
      generic: "Metformin Hydrochloride 500mg",
      mrp: 18.0,
      nppaCeiling: 22.0,
      isOvercharged: false,
      overcharge: 0,
    },
    {
      brand: "Meropenem 1g Injection",
      generic: "Meropenem 1000mg Powder for Injection",
      mrp: 1850.0,
      nppaCeiling: 950.0,
      isOvercharged: true,
      overcharge: 900.0,
    },
  ];

  return (
    <div className="card">
      <div style={{ marginBottom: "1.5rem" }}>
        <h2>{t.title}</h2>
        <p>{t.desc}</p>
      </div>

      <div
        style={{
          display: "flex",
          gap: "0.75rem",
          marginBottom: "1.5rem",
          flexWrap: "wrap",
        }}
      >
        <input
          type="text"
          className="input-field"
          style={{ flex: 1, minWidth: "240px" }}
          placeholder={t.searchPlaceholder}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="button" className="btn btn-primary">
          🔍 {t.searchBtn}
        </button>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>{t.brandName}</th>
              <th>{t.genericName}</th>
              <th>{t.mrp}</th>
              <th>{t.nppaCeiling}</th>
              <th>Compliance Status</th>
            </tr>
          </thead>
          <tbody>
            {sampleMedicines.map((med, idx) => (
              <tr key={idx}>
                <td style={{ fontWeight: 600 }}>{med.brand}</td>
                <td style={{ color: "var(--text-secondary)" }}>{med.generic}</td>
                <td>₹{med.mrp.toFixed(2)}</td>
                <td style={{ color: "var(--brand-cyan)", fontWeight: 600 }}>
                  ₹{med.nppaCeiling.toFixed(2)}
                </td>
                <td>
                  {med.isOvercharged ? (
                    <span className="badge badge-danger">
                      ⚠️ {t.statusOvercharged} (+₹{med.overcharge.toFixed(2)})
                    </span>
                  ) : (
                    <span className="badge badge-success">✓ {t.statusFair}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div
        style={{
          marginTop: "1.5rem",
          padding: "0.85rem 1rem",
          backgroundColor: "rgba(6, 182, 212, 0.08)",
          borderRadius: "var(--radius-md)",
          fontSize: "0.825rem",
          color: "var(--brand-cyan)",
        }}
      >
        💡 <strong>DPCO 2013 Provision:</strong> Charging above the notified NPPA ceiling price is an offence under the Essential Commodities Act, 1955. Retail pharmacies must mandatorily display generic bio-equivalents.
      </div>
    </div>
  );
};
