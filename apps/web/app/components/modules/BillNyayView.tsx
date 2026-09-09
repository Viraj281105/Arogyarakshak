"use client";

import React from "react";
import { Language, translations } from "../../translations";

interface BillNyayViewProps {
  currentLang: Language;
}

export const BillNyayView: React.FC<BillNyayViewProps> = ({ currentLang }) => {
  const t = translations[currentLang].modules.billnyay;

  const sampleItems = [
    {
      item: "ICU Day Charges (Deluxe Wing)",
      charged: 18500,
      cghs: 6500,
      overcharge: 12000,
      status: "Overcharged (184%)",
    },
    {
      item: "Disposable PPE Kit (per shift)",
      charged: 2400,
      cghs: 650,
      overcharge: 1750,
      status: "Exceeds Ceiling",
    },
    {
      item: "Syringe Infusion Pump Hire",
      charged: 1200,
      cghs: 350,
      overcharge: 850,
      status: "Bundled in ICU Tariff",
    },
    {
      item: "Paracetamol IV Infusion 100ml",
      charged: 450,
      cghs: 42,
      overcharge: 408,
      status: "Violates NPPA Ceiling",
    },
  ];

  const totalCharged = 72550;
  const totalCGHS = 34500;
  const totalSavings = totalCharged - totalCGHS;

  return (
    <div className="card">
      <div style={{ marginBottom: "1.5rem" }}>
        <h2>{t.title}</h2>
        <p>{t.desc}</p>
      </div>

      <div className="grid-3" style={{ marginBottom: "1.5rem" }}>
        <div className="stat-box">
          <div className="stat-label">{t.chargedTotal}</div>
          <div className="stat-val" style={{ color: "var(--text-primary)" }}>
            ₹{totalCharged.toLocaleString("en-IN")}
          </div>
        </div>

        <div className="stat-box">
          <div className="stat-label">{t.cghsBenchmark}</div>
          <div className="stat-val" style={{ color: "var(--brand-cyan)" }}>
            ₹{totalCGHS.toLocaleString("en-IN")}
          </div>
        </div>

        <div className="stat-box">
          <div className="stat-label">{t.potentialSavings}</div>
          <div className="stat-val" style={{ color: "var(--status-danger)" }}>
            ₹{totalSavings.toLocaleString("en-IN")}
          </div>
        </div>
      </div>

      <div style={{ marginBottom: "1rem" }}>
        <h3>{t.overchargesTitle}</h3>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>{t.itemCol}</th>
              <th>{t.chargedCol}</th>
              <th>{t.cghsCol}</th>
              <th>{t.varianceCol}</th>
              <th>Audit Status</th>
            </tr>
          </thead>
          <tbody>
            {sampleItems.map((row, idx) => (
              <tr key={idx}>
                <td style={{ fontWeight: 600 }}>{row.item}</td>
                <td>₹{row.charged.toLocaleString("en-IN")}</td>
                <td style={{ color: "var(--brand-cyan)" }}>₹{row.cghs.toLocaleString("en-IN")}</td>
                <td style={{ color: "var(--status-danger)", fontWeight: 700 }}>
                  +₹{row.overcharge.toLocaleString("en-IN")}
                </td>
                <td>
                  <span className="badge badge-danger">{row.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div
        style={{
          marginTop: "1.5rem",
          padding: "1rem",
          backgroundColor: "rgba(245, 158, 11, 0.08)",
          border: "1px solid rgba(245, 158, 11, 0.2)",
          borderRadius: "var(--radius-md)",
          fontSize: "0.85rem",
          color: "var(--status-warning)",
        }}
      >
        <strong>⚖️ {t.disputeGrounds}</strong>
      </div>
    </div>
  );
};
