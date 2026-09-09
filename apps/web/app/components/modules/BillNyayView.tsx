"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";
import { useApi } from "../../hooks/useApi";

// --- API Response Types (matching backend AuditResponse schema) ---
interface AuditResultItem {
  item_name: string;
  charged: number;
  cghs_benchmark: number;
  deviation_percentage: number;
  is_deviation: boolean;
}

interface AuditResponse {
  case_id: string;
  total_charged: number;
  total_benchmark: number;
  deviations_count: number;
  audit_items: AuditResultItem[];
}

interface BillNyayViewProps {
  currentLang: Language;
  caseId?: string;
}

export const BillNyayView: React.FC<BillNyayViewProps> = ({ currentLang, caseId }) => {
  const t = translations[currentLang].modules.billnyay;
  const api = useApi<AuditResponse>();
  const [hasRun, setHasRun] = useState(false);

  const handleRunAudit = async () => {
    if (!caseId) return;
    setHasRun(true);
    await api.execute(`/api/v1/billnyay/cases/${caseId}/audit`);
  };

  const auditData = api.data;
  const showExample = !hasRun && !caseId;

  // Example data shown only when no case is active, clearly labeled
  const exampleItems = [
    { item: "ICU Day Charges (Deluxe Wing)", charged: 18500, cghs: 6500, overcharge: 12000, status: "Overcharged (184%)" },
    { item: "Disposable PPE Kit (per shift)", charged: 2400, cghs: 650, overcharge: 1750, status: "Exceeds Ceiling" },
    { item: "Syringe Infusion Pump Hire", charged: 1200, cghs: 350, overcharge: 850, status: "Bundled in ICU Tariff" },
    { item: "Paracetamol IV Infusion 100ml", charged: 450, cghs: 42, overcharge: 408, status: "Violates NPPA Ceiling" },
  ];

  return (
    <div className="card">
      <div style={{ marginBottom: "1.5rem" }}>
        <h2>{t.title}</h2>
        <p>{t.desc}</p>
      </div>

      {/* Action Button */}
      {caseId && (
        <div style={{ marginBottom: "1.5rem" }}>
          <button
            type="button"
            className="btn btn-primary"
            style={{ width: "100%" }}
            onClick={handleRunAudit}
            disabled={api.loading}
          >
            {api.loading ? (
              <>
                <span className="step-indicator active" style={{ display: "inline-block", marginRight: "0.25rem" }} />
                Auditing bill against CGHS benchmarks...
              </>
            ) : (
              <>⚖️ Run CGHS Benchmark Audit</>
            )}
          </button>
        </div>
      )}

      {/* No Case Active Prompt */}
      {!caseId && !hasRun && (
        <div
          style={{
            padding: "1.25rem",
            marginBottom: "1.5rem",
            background: "rgba(6, 182, 212, 0.06)",
            border: "1px solid rgba(6, 182, 212, 0.2)",
            borderRadius: "var(--radius-md)",
            textAlign: "center",
            color: "var(--text-secondary)",
            fontSize: "0.9rem",
          }}
        >
          📤 Upload a hospital bill above to run a live CGHS benchmark audit.
        </div>
      )}

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

      {/* Real Audit Results */}
      {auditData && (
        <>
          <div className="grid-3" style={{ marginBottom: "1.5rem" }}>
            <div className="stat-box">
              <div className="stat-label">{t.chargedTotal}</div>
              <div className="stat-val" style={{ color: "var(--text-primary)" }}>
                ₹{auditData.total_charged.toLocaleString("en-IN")}
              </div>
            </div>
            <div className="stat-box">
              <div className="stat-label">{t.cghsBenchmark}</div>
              <div className="stat-val" style={{ color: "var(--brand-cyan)" }}>
                ₹{auditData.total_benchmark.toLocaleString("en-IN")}
              </div>
            </div>
            <div className="stat-box">
              <div className="stat-label">{t.potentialSavings}</div>
              <div className="stat-val" style={{ color: "var(--status-danger)" }}>
                ₹{(auditData.total_charged - auditData.total_benchmark).toLocaleString("en-IN")}
              </div>
            </div>
          </div>

          {auditData.audit_items.length > 0 ? (
            <>
              <div style={{ marginBottom: "1rem" }}>
                <h3>{t.overchargesTitle} ({auditData.deviations_count} flagged)</h3>
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
                    {auditData.audit_items.map((row, idx) => (
                      <tr key={idx}>
                        <td style={{ fontWeight: 600 }}>{row.item_name}</td>
                        <td>₹{row.charged.toLocaleString("en-IN")}</td>
                        <td style={{ color: "var(--brand-cyan)" }}>
                          ₹{row.cghs_benchmark.toLocaleString("en-IN")}
                        </td>
                        <td style={{ color: row.is_deviation ? "var(--status-danger)" : "var(--status-success)", fontWeight: 700 }}>
                          {row.is_deviation
                            ? `+₹${(row.charged - row.cghs_benchmark).toLocaleString("en-IN")} (${row.deviation_percentage}%)`
                            : "Within Benchmark"}
                        </td>
                        <td>
                          <span className={`badge ${row.is_deviation ? "badge-danger" : "badge-success"}`}>
                            {row.is_deviation ? `⚠️ Overcharged (${row.deviation_percentage}%)` : "✓ Fair"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div
              style={{
                padding: "1rem",
                textAlign: "center",
                color: "var(--text-secondary)",
                fontSize: "0.9rem",
              }}
            >
              No billing line items were found in the uploaded document for audit comparison.
            </div>
          )}

          {auditData.deviations_count > 0 && (
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
          )}
        </>
      )}

      {/* Example Data (only when no case active) */}
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
            ⓘ Example — Upload a real document to see live audit results
          </div>

          <div className="grid-3" style={{ marginBottom: "1.5rem", opacity: 0.7 }}>
            <div className="stat-box">
              <div className="stat-label">{t.chargedTotal}</div>
              <div className="stat-val" style={{ color: "var(--text-primary)" }}>₹72,550</div>
            </div>
            <div className="stat-box">
              <div className="stat-label">{t.cghsBenchmark}</div>
              <div className="stat-val" style={{ color: "var(--brand-cyan)" }}>₹34,500</div>
            </div>
            <div className="stat-box">
              <div className="stat-label">{t.potentialSavings}</div>
              <div className="stat-val" style={{ color: "var(--status-danger)" }}>₹38,050</div>
            </div>
          </div>

          <div style={{ marginBottom: "1rem" }}>
            <h3>{t.overchargesTitle}</h3>
          </div>

          <div className="table-wrapper" style={{ opacity: 0.7 }}>
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
                {exampleItems.map((row, idx) => (
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
        </>
      )}
    </div>
  );
};
