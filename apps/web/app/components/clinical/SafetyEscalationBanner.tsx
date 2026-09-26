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
  const [failure, setFailure] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    clinicalRequest<SafetyEvaluation>(clinicalPaths.safety(caseId), { caseToken })
      .then((data) => {
        if (cancelled) return;
        setEvaluation(data);
        setFailure(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setEvaluation(null);
        setFailure(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [caseId, caseToken]);

  // A safety check that failed must never look like one that found nothing.
  if (failure) {
    return (
      <div
        role="alert"
        style={{
          border: "1px solid var(--status-warning)",
          borderRadius: "var(--radius-md)",
          padding: "0.75rem 1rem",
          marginBottom: "1rem",
          fontSize: "0.85rem",
        }}
      >
        ⚠️ The clinical safety check could not be run ({failure}). No safety assessment has been made for this case.
        If you have urgent symptoms, seek medical care directly.
      </div>
    );
  }

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
      {evaluation.scope_note && <p style={{ fontSize: "0.7rem", opacity: 0.8 }}>{evaluation.scope_note}</p>}
    </section>
  );
};
