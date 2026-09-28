"use client";

import React, { useEffect, useState } from "react";
import { clinicalRequest } from "../lib/clinical";
import { TONE_CLASS, formatTimestamp } from "../lib/labels";
import { StatePanel } from "./clinical/StatePanel";

interface TimelineEvent {
  at: string;
  kind: string;
  label: string;
  detail: string | null;
  actor: "MACHINE" | "HUMAN" | "PATIENT";
}

interface TimelineResponse {
  events: TimelineEvent[];
  in_progress: { stage: string; message: string | null } | null;
  failure: { stage: string; message: string; recovery: string } | null;
  now: { medicines: number; medicines_checkable: number; medicines_held_back: number; medicines_human_reviewed: number };
}

const ACTOR: Record<TimelineEvent["actor"], { label: string; tone: keyof typeof TONE_CLASS }> = {
  MACHINE: { label: "Software", tone: "machine" },
  HUMAN: { label: "Human reviewer", tone: "human-authored" },
  PATIENT: { label: "You", tone: "neutral" },
};

/**
 * "What has happened to this case" — every step comes from a stored record with its own
 * timestamp (server: kadi.timeline), so nothing is shown before it happened. Current
 * state (how many medicines can be price-checked) is shown separately as "now".
 */
export const CaseTimeline: React.FC<{
  caseId: string;
  caseToken?: string;
  refreshKey: number;
  processing: boolean;
  failure: string | null;
}> = ({ caseId, caseToken, refreshKey, processing, failure }) => {
  const [tick, setTick] = useState(0);
  const key = `${caseId}|${refreshKey}|${processing}|${tick}`;
  const [result, setResult] = useState<{ key: string; data: TimelineResponse | null; error: string | null } | null>(null);

  useEffect(() => {
    let cancelled = false;
    clinicalRequest<TimelineResponse>(`/api/v1/kadi/cases/${encodeURIComponent(caseId)}/timeline`, { caseToken })
      .then((data) => !cancelled && setResult({ key, data, error: null }))
      .catch((err: unknown) => !cancelled && setResult((prev) => ({ key, data: prev?.data ?? null, error: err instanceof Error ? err.message : String(err) })));
    return () => {
      cancelled = true;
    };
  }, [caseId, caseToken, key]);

  const data = result?.data ?? null;
  const loading = result?.key !== key;

  return (
    <details className="card" style={{ marginBottom: "1.25rem" }} open>
      <summary style={{ cursor: "pointer", minHeight: "var(--min-touch-target, 44px)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <strong>What has happened to this case</strong>
        {data && <span style={{ fontSize: "0.8rem", opacity: 0.8 }}>({data.events.length} step{data.events.length === 1 ? "" : "s"})</span>}
      </summary>
      <div style={{ marginTop: "0.5rem", display: "grid", gap: "0.6rem" }}>
        {processing && (
          <StatePanel kind="loading">
            {data?.in_progress ? `In progress: ${data.in_progress.stage}. ` : "Processing… "}Steps appear here only once they have happened.
          </StatePanel>
        )}
        {data?.failure && (
          <StatePanel kind="error">
            {data.failure.stage}: {data.failure.message} {data.failure.recovery}
          </StatePanel>
        )}
        {!data?.failure && failure && !processing && <StatePanel kind="error">{failure}</StatePanel>}
        {result?.error && (
          <StatePanel kind="error" onRetry={() => setTick((n) => n + 1)}>
            Could not load the case history: {result.error}
          </StatePanel>
        )}
        {data && data.events.length === 0 && !processing && !data.failure && (
          <StatePanel kind="empty">Nothing has been recorded for this case yet.</StatePanel>
        )}
        {data && data.events.length > 0 && (
          <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: "0.45rem" }}>
            {data.events.map((e, i) => (
              <li key={`${e.at}-${i}`} style={{ borderLeft: "2px solid var(--border-subtle)", paddingLeft: "0.75rem", minWidth: 0 }}>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", alignItems: "center" }}>
                  <span style={{ fontSize: "0.75rem", opacity: 0.8 }} title={e.at}>
                    {formatTimestamp(e.at)}
                  </span>
                  <strong style={{ fontSize: "0.9rem" }}>{e.label}</strong>
                  <span className={TONE_CLASS[ACTOR[e.actor].tone]}>{ACTOR[e.actor].label}</span>
                </div>
                {e.detail && <div style={{ fontSize: "0.8rem", opacity: 0.9, overflowWrap: "anywhere" }}>{e.detail}</div>}
              </li>
            ))}
          </ol>
        )}
        {data && data.now.medicines > 0 && (
          <p style={{ margin: 0, fontSize: "0.85rem" }}>
            <strong>Now:</strong> {data.now.medicines_checkable} of {data.now.medicines} medicine(s) can be price-checked
            {data.now.medicines_held_back > 0 && <>; {data.now.medicines_held_back} held back until a human reads the entry</>}
            {data.now.medicines_human_reviewed > 0 && <>; {data.now.medicines_human_reviewed} read and agreed by independent human readers</>}.
          </p>
        )}
        <div>
          <button type="button" className="btn btn-secondary btn-compact" disabled={loading} onClick={() => setTick((n) => n + 1)}>
            {loading ? "Refreshing…" : "Refresh history"}
          </button>
        </div>
      </div>
    </details>
  );
};
