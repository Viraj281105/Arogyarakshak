"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";
import { useApi } from "../../hooks/useApi";

// --- API Response Type (matching backend MedicineBenchmark schema) ---
interface MedicineBenchmarkResponse {
  brand_name: string;
  active_ingredient: string;
  mrp: number;
  nppa_ceiling_price: number;
  is_overcharged: boolean;
  deviation_percentage: number;
  generic_substitute_available: boolean;
  generic_substitute_store_info: string;
}

interface DawaCheckViewProps {
  currentLang: Language;
}

export const DawaCheckView: React.FC<DawaCheckViewProps> = ({ currentLang }) => {
  const t = translations[currentLang].modules.dawacheck;
  const api = useApi<MedicineBenchmarkResponse>();
  const [brandName, setBrandName] = useState("Paracetamol 650mg");
  const [mrp, setMrp] = useState("3.5");
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async () => {
    const mrpVal = parseFloat(mrp);
    if (!brandName.trim() || isNaN(mrpVal) || mrpVal <= 0) return;
    setHasSearched(true);
    await api.execute("/api/v1/dawacheck/benchmark", {
      body: { brand_name: brandName.trim(), mrp: mrpVal },
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSearch();
    }
  };

  const result = api.data;
  const showExample = !hasSearched;

  // Example data shown only before first search, clearly labeled
  const exampleMedicines = [
    { brand: "Dolo 650mg Tablet (15s)", generic: "Paracetamol 650mg", mrp: 33.5, nppaCeiling: 28.5, isOvercharged: true, overcharge: 5.0 },
    { brand: "Augmentin 625 Duo Tablet (10s)", generic: "Amoxicillin (500mg) + Clavulanic Acid (125mg)", mrp: 220.0, nppaCeiling: 198.4, isOvercharged: true, overcharge: 21.6 },
    { brand: "Metformin 500mg SR Tablet (10s)", generic: "Metformin Hydrochloride 500mg", mrp: 18.0, nppaCeiling: 22.0, isOvercharged: false, overcharge: 0 },
    { brand: "Meropenem 1g Injection", generic: "Meropenem 1000mg Powder for Injection", mrp: 1850.0, nppaCeiling: 950.0, isOvercharged: true, overcharge: 900.0 },
  ];

  return (
    <div className="card">
      <div style={{ marginBottom: "1.5rem" }}>
        <h2>{t.title}</h2>
        <p>{t.desc}</p>
      </div>

      {/* Search Form */}
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
          style={{ flex: 2, minWidth: "200px" }}
          placeholder={t.searchPlaceholder}
          value={brandName}
          onChange={(e) => setBrandName(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <input
          type="number"
          className="input-field"
          style={{ flex: 1, minWidth: "120px" }}
          placeholder="MRP per unit (₹)"
          step="0.1"
          min="0"
          value={mrp}
          onChange={(e) => setMrp(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleSearch}
          disabled={api.loading}
        >
          {api.loading ? "Checking..." : `🔍 ${t.searchBtn}`}
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
        <div style={{ marginBottom: "1.5rem" }}>
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
                <tr>
                  <td style={{ fontWeight: 600 }}>{result.brand_name}</td>
                  <td style={{ color: "var(--text-secondary)" }}>{result.active_ingredient}</td>
                  <td>₹{result.mrp.toFixed(2)}</td>
                  <td style={{ color: "var(--brand-cyan)", fontWeight: 600 }}>
                    ₹{result.nppa_ceiling_price.toFixed(2)}
                  </td>
                  <td>
                    {result.is_overcharged ? (
                      <span className="badge badge-danger">
                        ⚠️ {t.statusOvercharged} (+{result.deviation_percentage}%)
                      </span>
                    ) : (
                      <span className="badge badge-success">✓ {t.statusFair}</span>
                    )}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Generic Substitute Info */}
          {result.generic_substitute_available && (
            <div
              style={{
                marginTop: "1rem",
                padding: "0.85rem 1rem",
                backgroundColor: "rgba(16, 185, 129, 0.08)",
                borderRadius: "var(--radius-md)",
                fontSize: "0.85rem",
                color: "var(--brand-emerald)",
              }}
            >
              💊 <strong>Generic Alternative:</strong> {result.generic_substitute_store_info}
            </div>
          )}
        </div>
      )}

      {/* Example Data (before first search) */}
      {showExample && (
        <>
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
            ⓘ Example — Enter a medicine name and MRP to check against NPPA ceiling prices
          </div>

          <div className="table-wrapper" style={{ opacity: 0.7 }}>
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
                {exampleMedicines.map((med, idx) => (
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
        </>
      )}

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
