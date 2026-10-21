"use client";

import React, { useEffect, useState } from "react";
import { Language, translations } from "../translations";
import { API_BASE, caseAuthHeaders } from "../hooks/useApi";
import { ResolutionDecision, formatScore, resolutionPaths, signalRows } from "../lib/resolution";
import { StatePanel } from "./clinical/StatePanel";

interface EntityResolutionReviewProps {
  caseId: string;
  caseToken?: string;
  currentLang: Language;
}

/**
 * "Are these the same?" prompts for Kadi's ASK decisions (#31). Nothing is merged until the
 * patient answers; each answer also feeds threshold calibration (#88).
 */
export const EntityResolutionReview: React.FC<EntityResolutionReviewProps> = ({ caseId, caseToken, currentLang }) => {
  const t = translations[currentLang].resolution;
  const [decisions, setDecisions] = useState<ResolutionDecision[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}${resolutionPaths.pending(caseId)}`, { headers: caseAuthHeaders(caseToken) })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<ResolutionDecision[]>;
      })
      .then((pending) => {
        if (cancelled) return;
        setDecisions(pending);
        setError(null);
        setLoaded(true);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
        setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [caseId, caseToken]);

  const answer = async (decision: ResolutionDecision, sameEntity: boolean) => {
    setBusyId(decision.id);
    try {
      const res = await fetch(`${API_BASE}${resolutionPaths.feedback(caseId, decision.id)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...caseAuthHeaders(caseToken) },
        body: JSON.stringify({ same_entity: sameEntity }),
      });
      // 409: already answered elsewhere, or the entities changed — either way it is no
      // longer a pending question.
      if (!res.ok && res.status !== 409) throw new Error(`HTTP ${res.status}`);
      setDecisions((prev) => prev.filter((d) => d.id !== decision.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  };

  const signalLabel = (signal: string) =>
    signal === "lexical" ? t.signalLexical : signal === "phonetic" ? t.signalPhonetic : t.signalSemantic;

  if (!loaded || (!error && decisions.length === 0)) return null;

  return (
    <section className="case-panel resolution" aria-labelledby="resolution-review-title">
      <div className="case-panel-head">
        <h3 id="resolution-review-title">{t.title}</h3>
        {decisions.length > 0 && <span className="timeline-count">{decisions.length} to answer</span>}
      </div>
      <p className="resolution-intro">{t.intro}</p>

      {error && <StatePanel kind="error">{error}</StatePanel>}

      {decisions.map((decision) => (
        <div key={decision.id} className="resolution-item">
          <div className="resolution-pair">
            <div className="resolution-name">
              <span className="stat-label">{t.mentionLabel}</span>
              <strong>{decision.mention_name}</strong>
            </div>
            <span className="resolution-vs" aria-hidden="true">≈ ?</span>
            <div className="resolution-name">
              <span className="stat-label">{t.existingLabel}</span>
              <strong>{decision.candidate_name}</strong>
            </div>
          </div>

          <ul className="resolution-signals">
            {signalRows(decision.signals).map((row) => (
              <li key={row.signal}>
                <span>{signalLabel(row.signal)}</span>
                <span className="code-tabular">{row.value ?? t.signalUnavailable}</span>
              </li>
            ))}
          </ul>
          <p className="resolution-confidence">
            {t.confidenceLabel}: {formatScore(decision.confidence)} · {t.uncalibratedNote}
          </p>

          <div className="resolution-actions">
            <button
              type="button"
              className="btn btn-primary btn-compact"
              disabled={busyId === decision.id}
              onClick={() => answer(decision, true)}
            >
              {t.confirmBtn}
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-compact"
              disabled={busyId === decision.id}
              onClick={() => answer(decision, false)}
            >
              {t.rejectBtn}
            </button>
          </div>
        </div>
      ))}
    </section>
  );
};
