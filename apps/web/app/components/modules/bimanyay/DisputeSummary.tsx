"use client";

import React from "react";
import { Language, translations } from "../../../translations";
import { ListenSummary } from "../../ListenSummary";
import { buildAppealSummary } from "../../../lib/listenSummaries";
import type { DisputeAuditResult } from "./types";

/** The grounds found, the heuristic score (shown as a rule-based estimate, never as a
 *  probability), the regulatory conflicts with their remedies, and the read-aloud summary. */
export function DisputeSummary({ result, currentLang }: { result: DisputeAuditResult; currentLang: Language }) {
  const t = translations[currentLang].modules.bimanyay;
  const heuristic = result.probability_basis === "HEURISTIC_PRIOR_NOT_HISTORICAL";
  const score = Math.round(result.reversal_probability_score * 100);

  return (
    <section className="case-panel bn-card" aria-labelledby="bm-grounds-title">
      <div className="case-panel-head">
        <h3 id="bm-grounds-title">What the denial check found</h3>
        <span className={`badge ${result.is_wrongful_denial ? "badge-success" : "badge-warning"}`}>
          {result.is_wrongful_denial ? t.wrongfulBadge : "No clear rule-based ground found"}
        </span>
      </div>

      <div className="bm-verdict">
        <div className="bm-grounds">
          <p className="bn-summary">{result.primary_dispute_grounds}</p>
        </div>
        <figure className="bm-estimate">
          <figcaption>{t.reversalScore}</figcaption>
          <div className="bm-estimate-value">
            <span className="code-tabular">{score}</span>
            <small>/ 100</small>
          </div>
          <div
            className="bm-estimate-bar"
            role="img"
            aria-label={`${t.reversalScore}: ${score} out of 100. ${heuristic ? t.heuristicDisclosure : ""}`}
          >
            <span style={{ width: `${score}%` }} />
          </div>
          {/* A missing basis is never upgraded to a probability; the disclosure always shows. */}
          <p className="bn-fine">{t.heuristicDisclosure}</p>
        </figure>
      </div>

      <h4 className="bm-subhead">{t.violationsTitle}</h4>
      {result.regulatory_violations.length > 0 ? (
        <ul className="bm-violations">
          {result.regulatory_violations.map((v, idx) => (
            <li key={idx} className="bm-violation">
              <span className="bm-violation-source">
                {v.statute_or_circular}
                {v.clause_reference && <span className="code-tabular"> · {v.clause_reference}</span>}
              </span>
              <p>{v.violation_summary}</p>
              {v.legal_remedy && (
                <p className="bm-remedy">
                  <strong>Suggested remedy:</strong> {v.legal_remedy}
                </p>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="bn-fine">No specific rule conflict was recorded for this denial category.</p>
      )}

      <ListenSummary
        lang={currentLang}
        panel="appeal"
        summary={buildAppealSummary(
          {
            isWrongfulDenial: result.is_wrongful_denial,
            violationCount: result.regulatory_violations.length,
            reversalScore: result.reversal_probability_score,
            heuristic,
          },
          currentLang
        )}
      />
    </section>
  );
}
