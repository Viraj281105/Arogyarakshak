"use client";

import React from "react";
import { Language, translations } from "../../../translations";
import { ListenSummary } from "../../ListenSummary";
import { buildDeadlineSummary } from "../../../lib/listenSummaries";
import { ExplainTrail } from "../../ExplainTrail";
import { StatePanel } from "../../clinical/StatePanel";
import { TimelineChart } from "../../ui/Charts";
import type { GrievanceTrackerResponse } from "./types";
import { useT } from "../../../i18n/useT";
import { LOCALE, msg } from "../../../i18n/format";

// Statutory SLA tier states (bimanyay.tracker) in plain language.
const SLA_STATUS_LABEL: Record<string, string> = {
  ACTIVE: msg("Current step"),
  OVERDUE: msg("Deadline passed"),
  COMPLETED: "Done",
  PENDING: msg("Later step"),
};

const STATUS_CLASS: Record<string, string> = {
  ACTIVE: "is-active",
  OVERDUE: "is-overdue",
  COMPLETED: "is-done",
};

/** Whole calendar days from today to an ISO date (negative once it has passed). */
function daysUntil(iso: string): number | null {
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((d.getTime() - today.getTime()) / 86_400_000);
}

const formatDate = (iso: string, lang: Language) => {
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString(LOCALE[lang], { day: "numeric", month: "short", year: "numeric" });
};

/** The statutory grievance deadlines (bimanyay.tracker), each with its explanation trail;
 *  before they are calculated, the three escalation tiers in general terms. */
export function SlaTimeline({
  timeline,
  loading,
  error,
  countedFrom,
  insurerName,
  currentLang,
}: {
  timeline: GrievanceTrackerResponse | null;
  loading: boolean;
  error?: string | null;
  countedFrom?: string | null;
  insurerName: string;
  currentLang: Language;
}) {
  const tr = useT();
  const t = translations[currentLang].modules.bimanyay;
  const events = timeline?.timeline_events ?? [];

  return (
    <section className="case-panel bn-card" aria-labelledby="bm-deadlines-title">
      <div className="case-panel-head">
        <h3 id="bm-deadlines-title">{t.timelineTitle}</h3>
      </div>
      {countedFrom && events.length > 0 && (
        <p className="bn-fine">{tr("Counted from today ({value}), assuming you send the step-1 appeal today. Calendar days; holidays are not applied.", { value: formatDate(countedFrom, currentLang) })}</p>
      )}
      {events.length > 0 && (
        <ListenSummary lang={currentLang} panel="deadline" summary={buildDeadlineSummary(events, currentLang)} />
      )}
      {error && <StatePanel kind="error">{tr("Could not calculate the deadlines: {error}", { error: error })}</StatePanel>}

      {events.length > 0 ? (
        <>
          <TimelineChart
            title={tr("Statutory escalation deadlines")}
            locale={LOCALE[currentLang]}
            source={tr("IRDAI Master Circular (29 May 2024)")}
            units={tr("Calendar date")}
            period={countedFrom ? tr("Counted from {value}", { value: formatDate(countedFrom, currentLang) }) : tr("3-tier progression")}
            events={events.map((ev) => ({
              date: ev.deadline_date,
              label: ev.title,
              detail: SLA_STATUS_LABEL[ev.status] ? tr(SLA_STATUS_LABEL[ev.status]) : ev.status,
            }))}
          />
          <ol className="timeline bm-deadlines">
          {events.map((event, idx) => {
            const days = daysUntil(event.deadline_date);
            return (
              <li key={idx} className={`timeline-event bm-deadline ${STATUS_CLASS[event.status] ?? ""}`}>
                <span className="timeline-dot" aria-hidden="true" />
                <div className="bm-deadline-head">
                  <strong className="timeline-label">{event.title}</strong>
                  <span className={`badge ${event.status === "ACTIVE" ? "badge-info" : event.status === "OVERDUE" ? "badge-danger" : "badge-demo"}`}>
                    {SLA_STATUS_LABEL[event.status] ? tr(SLA_STATUS_LABEL[event.status]) : event.status}
                  </span>
                </div>
                <div className="bm-deadline-date">
                  <time dateTime={event.deadline_date} className="code-tabular">
                    {formatDate(event.deadline_date, currentLang)}
                  </time>
                  {days !== null && (
                    <span className={days < 0 ? "is-past" : ""}>
                      {days > 1
                        ? tr("in {days} days", { days })
                        : days === 1
                          ? tr("in 1 day")
                          : days === 0
                            ? tr("today")
                            : days === -1
                              ? tr("1 day ago")
                              : tr("{days} days ago", { days: -days })}
                    </span>
                  )}
                </div>
                <p className="timeline-detail">{event.instructions}</p>
                <ExplainTrail explanation={event.explanation} lang={currentLang} />
              </li>
            );
          })}
        </ol>
        </>
      ) : loading ? (
        <StatePanel kind="loading">{tr("Calculating the escalation deadlines…")}</StatePanel>
      ) : (
        <ol className="timeline bm-deadlines">
          {[
            { label: t.tier1Label, desc: t.tier1Desc.replace("{insurer}", insurerName || t.insurerName), badge: t.activeBadge, active: true },
            { label: t.tier2Label, desc: t.tier2Desc, badge: t.pendingBadge, active: false },
            { label: t.tier3Label, desc: t.tier3Desc, badge: t.pendingBadge, active: false },
          ].map((tier) => (
            <li key={tier.label} className={`timeline-event bm-deadline ${tier.active ? "is-active" : ""}`}>
              <span className="timeline-dot" aria-hidden="true" />
              <div className="bm-deadline-head">
                <strong className="timeline-label">{tier.label}</strong>
                <span className={`badge ${tier.active ? "badge-info" : "badge-demo"}`}>{tier.badge}</span>
              </div>
              <p className="timeline-detail">{tier.desc}</p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
