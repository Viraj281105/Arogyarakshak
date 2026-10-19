"use client";

import React from "react";
import { Language, translations } from "../../../translations";
import { ListenSummary } from "../../ListenSummary";
import { buildAppealSummary } from "../../../lib/listenSummaries";
import type { DisputeAuditResult } from "./types";

/** The heuristic reversal score (disclosed as such), the statutory violations found, and
 *  the read-aloud summary. */
export function DisputeSummary({ result, currentLang }: { result: DisputeAuditResult; currentLang: Language }) {
  const t = translations[currentLang].modules.bimanyay;
  return (
    <>
      <div className="grid-2" style={{ marginBottom: "1.5rem" }}>
        <div className="stat-box" style={{ borderLeft: `4px solid ${result.is_wrongful_denial ? "var(--status-success)" : "var(--status-danger)"}` }}>
          <div className="stat-label">{t.reversalScore}</div>
          <div className="stat-val" style={{ color: result.is_wrongful_denial ? "var(--brand-emerald)" : "var(--status-danger)" }}>
            {(result.reversal_probability_score * 100).toFixed(0)}%
          </div>
          <div style={{ fontSize: "0.75rem", opacity: 0.8, marginTop: "0.35rem" }}>{t.heuristicDisclosure}</div>
          {result.is_wrongful_denial && (
            <span className="badge badge-success" style={{ marginTop: "0.5rem" }}>
              ✓ {t.wrongfulBadge}
            </span>
          )}
        </div>

        <div className="stat-box" style={{ borderLeft: "4px solid var(--brand-cyan)" }}>
          <div className="stat-label">{t.violationsTitle}</div>
          {result.regulatory_violations.length > 0 ? (
            <ul style={{ listStyle: "none", marginTop: "0.5rem", fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
              {result.regulatory_violations.map((v, idx) => (
                <li key={idx}>
                  <strong style={{ color: "var(--brand-cyan)" }}>{v.statute_or_circular}:</strong>{" "}
                  {v.clause_reference} — {v.violation_summary}
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ fontSize: "0.85rem", marginTop: "0.5rem", color: "var(--text-secondary)" }}>
              {result.primary_dispute_grounds}
            </p>
          )}
        </div>
      </div>

      <ListenSummary
        lang={currentLang}
        panel="appeal"
        summary={buildAppealSummary(
          {
            isWrongfulDenial: result.is_wrongful_denial,
            violationCount: result.regulatory_violations.length,
            reversalScore: result.reversal_probability_score,
            heuristic: result.probability_basis === "HEURISTIC_PRIOR_NOT_HISTORICAL",
          },
          currentLang
        )}
      />
    </>
  );
}
