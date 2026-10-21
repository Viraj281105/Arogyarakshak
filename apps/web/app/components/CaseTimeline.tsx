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
    <details className="case-panel timeline-panel" open>
      <summary className="case-panel-head timeline-summary">
        <h3>What has happened to this case</h3>
        {data && (
          <span className="timeline-count">
            {data.events.length} step{data.events.length === 1 ? "" : "s"}
          </span>
        )}
      </summary>
      <div className="timeline-body">
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
        {!data && !result?.error && <p className="timeline-loading">Loading the case history…</p>}
        {data && data.events.length > 0 && (
          <ol className="timeline">
            {data.events.map((e, i) => (
              <li key={`${e.at}-${i}`} className={`timeline-event actor-${e.actor.toLowerCase()}`}>
                <span className="timeline-dot" aria-hidden="true" />
                <div className="timeline-meta">
                  <time dateTime={e.at} title={e.at}>
                    {formatTimestamp(e.at)}
                  </time>
                  <span className={TONE_CLASS[ACTOR[e.actor].tone]}>{ACTOR[e.actor].label}</span>
                </div>
                <strong className="timeline-label">{e.label}</strong>
                {e.detail && <p className="timeline-detail">{e.detail}</p>}
              </li>
            ))}
          </ol>
        )}
        {data && data.now.medicines > 0 && (
          <p className="timeline-now">
            <strong>Now:</strong> {data.now.medicines_checkable} of {data.now.medicines} medicine(s) can be price-checked
            {data.now.medicines_held_back > 0 && <>; {data.now.medicines_held_back} held back until a human reads the entry</>}
            {data.now.medicines_human_reviewed > 0 && <>; {data.now.medicines_human_reviewed} read and agreed by independent human readers</>}.
          </p>
        )}
        <button type="button" className="btn btn-ghost btn-compact" disabled={loading} onClick={() => setTick((n) => n + 1)}>
          <svg width="15" height="15" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
            <path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7" />
          </svg>
          {loading ? "Refreshing…" : "Refresh history"}
        </button>
      </div>
    </details>
  );
};
