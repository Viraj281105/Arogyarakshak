"use client";

import React, { useEffect, useState } from "react";
import { SafetyEvaluation, clinicalPaths, clinicalRequest } from "../../lib/clinical";

/**
 * Shows red-flag escalations from ACTIVE, board-approved safety rules. Always shows the
 * source protocol, the rule version and the floor disclaimer; never implies that "no
 * escalation" means "safe".
 */
export const SafetyEscalationBanner: React.FC<{ caseId: string; caseToken?: string }> = ({ caseId, caseToken }) => {
  const [evaluation, setEvaluation] = useState<SafetyEvaluation | null>(null);

  useEffect(() => {
    let cancelled = false;
    clinicalRequest<SafetyEvaluation>(clinicalPaths.safety(caseId), { caseToken })
      .then((data) => !cancelled && setEvaluation(data))
      .catch(() => !cancelled && setEvaluation(null));
    return () => {
      cancelled = true;
    };
  }, [caseId, caseToken]);

  if (!evaluation) return null;

  if (evaluation.escalations.length === 0) {
    return (
      <p style={{ fontSize: "0.75rem", opacity: 0.75, marginBottom: "1rem" }}>
        🛡️ {evaluation.coverage_note} {evaluation.disclaimer}
      </p>
    );
  }

  return (
    <section
      role="alert"
      aria-labelledby="safety-escalation-title"
      style={{
        border: "2px solid var(--status-danger)",
        background: "rgba(239, 68, 68, 0.1)",
        borderRadius: "var(--radius-md)",
        padding: "1rem 1.25rem",
        marginBottom: "1.5rem",
      }}
    >
      <h3 id="safety-escalation-title" style={{ color: "var(--status-danger)" }}>
        ⚠️ Clinical safety check
      </h3>
      {evaluation.escalations.map((esc) => (
        <div key={esc.rule_id} style={{ marginTop: "0.75rem" }}>
          <strong>
            {esc.severity === "URGENT" ? "Urgent: " : ""}
            {esc.title}
          </strong>
          <p style={{ margin: "0.25rem 0" }}>{esc.message}</p>
          <p style={{ fontSize: "0.8rem" }}>
            Matched words: {esc.matched_terms.join(", ")} · Rule v{esc.rule_version} · Source: {esc.source.name}
            {esc.source.version ? ` (${esc.source.version})` : ""}
            {esc.source.section ? `, ${esc.source.section}` : ""}
          </p>
          <ul style={{ fontSize: "0.75rem", paddingLeft: "1.1rem", opacity: 0.85 }}>
            {esc.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
          {esc.human_review_recommended && (
            <p style={{ fontSize: "0.8rem" }}>A human clinician should assess this; ArogyaRakshak cannot.</p>
          )}
          {esc.rule_review_overdue && (
            <p style={{ fontSize: "0.75rem", color: "var(--status-warning)" }}>This rule is past its scheduled review date.</p>
          )}
        </div>
      ))}
      <p style={{ fontSize: "0.75rem", marginTop: "0.75rem" }}>{evaluation.disclaimer}</p>
    </section>
  );
};
