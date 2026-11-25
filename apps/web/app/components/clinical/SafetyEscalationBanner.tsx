"use client";

import React, { useEffect, useState } from "react";
import { SafetyEvaluation, clinicalPaths, clinicalRequest } from "../../lib/clinical";
import { useT } from "../../i18n/useT";

/**
 * Shows red-flag escalations from ACTIVE, board-approved safety rules. Always shows the
 * source protocol, the rule version and the floor disclaimer; never implies that "no
 * escalation" means "safe".
 */
export const SafetyEscalationBanner: React.FC<{ caseId: string; caseToken?: string }> = ({ caseId, caseToken }) => {
  const tr = useT();
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

  // A safety check that failed must never look like one that found nothing — whether the
  // request failed or the server reports the rules could not be evaluated.
  const unavailable = failure !== null || evaluation?.status === "UNAVAILABLE";
  if (unavailable) {
    return (
      <div role="alert" className="safety-card is-unavailable">
        <SafetyIcon />
        <div>
          <strong>{tr("Safety check unavailable.")}</strong>{" "}
          {tr("The clinical safety check could not be run. No safety assessment has been made for this case — this is not the same as \"nothing found\". If you have urgent symptoms, seek medical care directly.")}
          {failure ? ` (${failure})` : ""}
        </div>
      </div>
    );
  }

  if (!evaluation) return null;

  if (evaluation.escalations.length === 0) {
    return (
      <div className="safety-card is-quiet">
        <SafetyIcon />
        <p>
          <strong>{tr("Safety check:")}</strong> {evaluation.coverage_note} {evaluation.disclaimer}
        </p>
      </div>
    );
  }

  return (
    <section role="alert" aria-labelledby="safety-escalation-title" className="safety-card is-escalated">
      <SafetyIcon />
      <div>
        <h3 id="safety-escalation-title">{tr("Clinical safety check")}</h3>
        {evaluation.escalations.map((esc) => (
          <div key={esc.rule_id} className="safety-escalation">
            <strong>
              {esc.severity === "URGENT" && (
                <>
                  <span className="safety-urgent">{tr("Urgent")}</span>{" "}
                </>
              )}
              {esc.title}
            </strong>
            <p>{esc.message}</p>
            <p className="safety-source">{tr("Matched words:")}{" "}{esc.matched_terms.join(", ")}{" "}{tr("· Rule v")}{esc.rule_version}{" "}{tr("· Source:")}{" "}{esc.source.name}
              {esc.source.version ? ` (${esc.source.version})` : ""}
              {esc.source.section ? `, ${esc.source.section}` : ""}
            </p>
            <ul className="safety-limits">
              {esc.limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
            {esc.human_review_recommended && <p>{tr("A human clinician should assess this; ArogyaRakshak cannot.")}</p>}
            {esc.rule_review_overdue && <p className="safety-overdue">{tr("This rule is past its scheduled review date.")}</p>}
          </div>
        ))}
        <p className="safety-disclaimer">{evaluation.disclaimer}</p>
        {evaluation.scope_note && <p className="safety-disclaimer">{evaluation.scope_note}</p>}
      </div>
    </section>
  );
};

const SafetyIcon: React.FC = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon safety-icon">
    <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM12 8v5M12 16h.01" />
  </svg>
);
