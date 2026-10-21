"use client";

import React from "react";
import { Language, translations } from "../../../translations";
import { ExplainTrail } from "../../ExplainTrail";
import type { AuditResponse } from "./types";

/** CGHS audit totals, the coverage disclosure, and the per-line table with each line's
 *  "Why am I seeing this?" trail. An unmatched line is never shown as fair. */
export function AuditResults({ audit, currentLang }: { audit: AuditResponse; currentLang: Language }) {
  const t = translations[currentLang].modules.billnyay;
  return (
    <>
      <div className="grid-3" style={{ marginBottom: "1.5rem" }}>
        <div className="stat-box">
          <div className="stat-label">{t.chargedTotal}</div>
          <div className="stat-val" style={{ color: "var(--text-primary)" }}>
            ₹{audit.total_charged.toLocaleString("en-IN")}
          </div>
        </div>
        <div className="stat-box">
          <div className="stat-label">{t.cghsBenchmark}</div>
          <div className="stat-val" style={{ color: "var(--brand-cyan)" }}>
            ₹{audit.total_benchmark.toLocaleString("en-IN")}
          </div>
        </div>
        <div className="stat-box">
          <div className="stat-label">{t.potentialSavings}</div>
          <div className="stat-val" style={{ color: "var(--status-danger)" }}>
            ₹{audit.potential_savings.toLocaleString("en-IN")}
          </div>
        </div>
      </div>

      {/* Coverage disclosure: the patient must be able to see how much of the
          bill was actually compared against a benchmark. */}
      {audit.unmatched_count > 0 && (
        <div
          style={{
            padding: "0.75rem 1rem",
            marginBottom: "1.5rem",
            background: "rgba(245, 158, 11, 0.08)",
            border: "1px solid rgba(245, 158, 11, 0.25)",
            borderRadius: "var(--radius-md)",
            fontSize: "0.85rem",
            color: "var(--status-warning)",
          }}
        >
          ⓘ {t.unmatchedNotice
            .replace("{count}", String(audit.unmatched_count))
            .replace("{amount}", `₹${audit.unmatched_amount.toLocaleString("en-IN")}`)}
        </div>
      )}

      {audit.audit_items.length > 0 ? (
        <>
          <div style={{ marginBottom: "1rem" }}>
            <h3>{t.overchargesTitle} ({audit.deviations_count} flagged)</h3>
          </div>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>{t.itemCol}</th>
                  <th>{t.chargedCol}</th>
                  <th>{t.cghsCol}</th>
                  <th>{t.varianceCol}</th>
                  <th>{t.statusCol}</th>
                </tr>
              </thead>
              <tbody>
                {audit.audit_items.map((row, idx) => {
                  const benchmarked = row.benchmarked && row.cghs_benchmark !== null;
                  return (
                    <React.Fragment key={idx}>
                    <tr>
                      <td style={{ fontWeight: 600 }}>{row.item_name}</td>
                      <td>₹{row.charged.toLocaleString("en-IN")}</td>
                      <td style={{ color: benchmarked ? "var(--brand-cyan)" : "var(--text-secondary)" }}>
                        {benchmarked
                          ? `₹${(row.cghs_benchmark as number).toLocaleString("en-IN")}`
                          : "—"}
                        {row.benchmark_basis && (
                          <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)", fontWeight: 400 }}>
                            {row.benchmark_basis}
                          </div>
                        )}
                      </td>
                      <td
                        style={{
                          color: !benchmarked
                            ? "var(--text-secondary)"
                            : row.is_deviation
                            ? "var(--status-danger)"
                            : "var(--status-success)",
                          fontWeight: 700,
                        }}
                      >
                        {!benchmarked
                          ? row.not_benchmarked_reason ?? t.notBenchmarked
                          : row.is_deviation
                          ? `+₹${(row.charged - (row.cghs_benchmark as number)).toLocaleString("en-IN")} (${row.deviation_percentage}%)`
                          : t.withinBenchmark}
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            !benchmarked
                              ? "badge-warning"
                              : row.is_deviation
                              ? "badge-danger"
                              : "badge-success"
                          }`}
                        >
                          {!benchmarked
                            ? `ⓘ ${t.notBenchmarkedBadge}`
                            : row.status === "bundled"
                            ? `⚠️ ${t.bundledBadge}`
                            : row.is_deviation
                            ? `⚠️ ${t.overchargedBadge} (${row.deviation_percentage}%)`
                            : `✓ ${t.fairBadge}`}
                        </span>
                      </td>
                    </tr>
                    {row.explanation && (
                      <tr>
                        <td colSpan={5} style={{ paddingTop: 0 }}>
                          <ExplainTrail explanation={row.explanation} lang={currentLang} />
                        </td>
                      </tr>
                    )}
                    </React.Fragment>
                  );
                })}
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

      {audit.deviations_count > 0 && (
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
  );
}
