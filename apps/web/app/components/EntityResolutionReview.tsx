"use client";

import React, { useEffect, useState } from "react";
import { Language, translations } from "../translations";
import { API_BASE, caseAuthHeaders } from "../hooks/useApi";
import { ResolutionDecision, formatScore, resolutionPaths, signalRows } from "../lib/resolution";

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
    <section className="card" style={{ marginBottom: "1.5rem" }} aria-labelledby="resolution-review-title">
      <h3 id="resolution-review-title">{t.title}</h3>
      <p style={{ fontSize: "0.9rem", marginBottom: "1rem" }}>{t.intro}</p>

      {error && (
        <div role="alert" style={{ color: "#fca5a5", fontSize: "0.85rem", marginBottom: "0.75rem" }}>
          ⚠️ {error}
        </div>
      )}

      {decisions.map((decision) => (
        <div
          key={decision.id}
          style={{
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-md)",
            padding: "1rem",
            marginBottom: "0.75rem",
          }}
        >
          <div className="grid-2" style={{ marginBottom: "0.75rem" }}>
            <div>
              <div className="stat-label">{t.mentionLabel}</div>
              <strong>{decision.mention_name}</strong>
            </div>
            <div>
              <div className="stat-label">{t.existingLabel}</div>
              <strong>{decision.candidate_name}</strong>
            </div>
          </div>

          <ul style={{ listStyle: "none", fontSize: "0.8rem", marginBottom: "0.5rem" }}>
            {signalRows(decision.signals).map((row) => (
              <li key={row.signal}>
                {signalLabel(row.signal)}: {row.value ?? t.signalUnavailable}
              </li>
            ))}
          </ul>
          <div style={{ fontSize: "0.75rem", marginBottom: "0.75rem", opacity: 0.8 }}>
            {t.confidenceLabel}: {formatScore(decision.confidence)} · {t.uncalibratedNote}
          </div>

          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <button
              type="button"
              className="btn btn-primary"
              disabled={busyId === decision.id}
              onClick={() => answer(decision, true)}
            >
              {t.confirmBtn}
            </button>
            <button
              type="button"
              className="btn"
              style={{ border: "1px solid var(--border-subtle)" }}
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
