"use client";

import React, { useEffect, useMemo, useState } from "react";
import { ErrorState, EmptyState, LoadingState } from "../ui/States";
import { StatusBadge } from "../ui/Badges";
import { casePath, getCaseJson } from "../../lib/caseApi";
import { useLanguage } from "../../shell/ShellProvider";
import { useCase } from "./CaseProvider";
import { caseCopy, type CaseCopy } from "./caseCopy";
import { timelineCopy, type TimelineCopy } from "./timelineCopy";
import { fillCopy, formatDateTime } from "./workspaceFormat";

type WsCopy = CaseCopy & TimelineCopy;

export interface TimelineEvent {
  at: string;
  kind: string;
  label: string;
  detail: string | null;
  actor: "MACHINE" | "HUMAN" | "PATIENT";
}

export interface TimelineResponse {
  events: TimelineEvent[];
  in_progress: { stage: string; message: string | null } | null;
  failure: { stage: string; message: string; recovery: string } | null;
  now?: { medicines: number; medicines_checkable: number; medicines_held_back: number; medicines_human_reviewed: number };
}

/** Pure: the events whose kind is in `kinds` (all when empty), newest first or oldest first. */
export function filterTimeline(events: readonly TimelineEvent[], kinds: ReadonlySet<string>, newestFirst: boolean): TimelineEvent[] {
  const kept = kinds.size === 0 ? [...events] : events.filter((e) => kinds.has(e.kind));
  return newestFirst ? kept.reverse() : kept;
}

/**
 * Timeline explorer over GET /cases/{id}/timeline: every step comes from a stored record with its
 * own timestamp (kadi.timeline), so nothing is shown before it happened. Filter by kind of step,
 * change the order; the event text is the server's (English) wording.
 */
export function TimelineExplorer({ refreshKey }: { refreshKey: number }) {
  const [lang] = useLanguage();
  const c = { ...caseCopy[lang], ...timelineCopy[lang] };
  const cs = useCase();
  const ref = cs.ref;
  const [data, setData] = useState<TimelineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [kinds, setKinds] = useState<Set<string>>(new Set());
  const [newestFirst, setNewestFirst] = useState(false);

  useEffect(() => {
    if (!ref) return;
    let cancelled = false;
    getCaseJson<TimelineResponse>(ref, `${casePath(ref.id)}/timeline`)
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setError(null);
      })
      .catch((err: unknown) => !cancelled && setError(err instanceof Error ? err.message : String(err)));
    return () => {
      cancelled = true;
    };
  }, [ref, refreshKey, tick]);

  const available = useMemo(() => [...new Set((data?.events ?? []).map((e) => e.kind))], [data]);
  const shown = useMemo(() => filterTimeline(data?.events ?? [], kinds, newestFirst), [data, kinds, newestFirst]);

  const toggle = (k: string) =>
    setKinds((prev) => {
      const next = new Set(prev);
      if (next.has(k)) next.delete(k);
      else next.add(k);
      return next;
    });

  return (
    <section className="ws-section" aria-labelledby="ws-timeline-title">
      <h2 id="ws-timeline-title" className="ws-section-title">
        {c.timeline.title}
      </h2>
      <p className="ws-section-lede">{c.timeline.lede}</p>
      {error ? (
        <ErrorState
          title={c.timeline.error}
          action={
            <button type="button" className="btn btn-secondary btn-compact" onClick={() => setTick((n) => n + 1)}>
              {c.common.retry}
            </button>
          }
        >
          <p>{error}</p>
        </ErrorState>
      ) : !data ? (
        <LoadingState label={c.common.loading} minHeight="8rem" />
      ) : (
        <>
          {data.failure && (
            <ErrorState title={data.failure.stage}>
              <p>
                {data.failure.message} {data.failure.recovery}
              </p>
            </ErrorState>
          )}
          {data.in_progress && <LoadingState label={fillCopy(c.timeline.inProgress, { stage: data.in_progress.stage })} minHeight="4rem" />}
          {data.events.length === 0 ? (
            <EmptyState title={c.timeline.empty} />
          ) : (
            <>
              <div className="ws-filters" role="group" aria-label={c.timeline.filterLabel}>
                {available.map((k) => (
                  <button key={k} type="button" className="ws-chip" aria-pressed={kinds.has(k)} onClick={() => toggle(k)}>
                    {c.timeline.kinds[k as keyof WsCopy["timeline"]["kinds"]] ?? k}
                  </button>
                ))}
                <button type="button" className="ws-chip" aria-pressed={newestFirst} onClick={() => setNewestFirst((v) => !v)}>
                  {c.timeline.newestFirst}
                </button>
              </div>
              <p className="ws-muted" role="status">
                {fillCopy(c.timeline.count, { shown: shown.length, total: data.events.length })}
              </p>
              <ol className="ws-timeline">
                {shown.map((e, i) => (
                  <li key={`${e.at}-${e.kind}-${i}`} className="ws-timeline-event">
                    <div className="ws-timeline-meta">
                      <time dateTime={e.at}>{formatDateTime(e.at, lang)}</time>
                      <StatusBadge tone={e.actor === "HUMAN" ? "success" : e.actor === "PATIENT" ? "info" : "neutral"}>{c.timeline.actors[e.actor]}</StatusBadge>
                    </div>
                    <p className="ws-action-title" lang="en">
                      {e.label}
                    </p>
                    {e.detail && (
                      <p className="ws-muted" lang="en">
                        {e.detail}
                      </p>
                    )}
                  </li>
                ))}
              </ol>
            </>
          )}
          {data.now && data.now.medicines > 0 && (
            <p className="ws-muted">
              {fillCopy(c.timeline.now, { checkable: data.now.medicines_checkable, total: data.now.medicines, held: data.now.medicines_held_back })}
            </p>
          )}
        </>
      )}
    </section>
  );
}
