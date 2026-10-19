"use client";

import React from "react";
import { Language, translations } from "../../../translations";
import { ListenSummary } from "../../ListenSummary";
import { buildDeadlineSummary } from "../../../lib/listenSummaries";
import { ExplainTrail } from "../../ExplainTrail";
import type { GrievanceTrackerResponse } from "./types";

// Statutory SLA tier states (bimanyay.tracker) in plain language.
const SLA_STATUS_LABEL: Record<string, string> = {
  ACTIVE: "Current step",
  OVERDUE: "Deadline passed",
  COMPLETED: "Done",
  PENDING: "Later step",
};

const PENDING_BADGE: React.CSSProperties = { background: "rgba(255,255,255,0.08)", color: "var(--text-muted)" };

/** The statutory grievance deadlines (bimanyay.tracker), each with its explanation trail;
 *  before they are calculated, the three escalation tiers in general terms. */
export function SlaTimeline({
  timeline,
  loading,
  insurerName,
  currentLang,
}: {
  timeline: GrievanceTrackerResponse | null;
  loading: boolean;
  insurerName: string;
  currentLang: Language;
}) {
  const t = translations[currentLang].modules.bimanyay;
  return (
    <div>
      <h3>⏳ {t.timelineTitle}</h3>
      {timeline && timeline.timeline_events.length > 0 && (
        <ListenSummary lang={currentLang} panel="deadline" summary={buildDeadlineSummary(timeline.timeline_events, currentLang)} />
      )}
      {timeline && timeline.timeline_events.length > 0 ? (
        <div className="timeline-list">
          {timeline.timeline_events.map((event, idx) => {
            const isActive = event.status === "ACTIVE";
            const isOverdue = event.status === "OVERDUE";
            const badgeClass = isActive ? "badge-info" : isOverdue ? "badge-danger" : "";
            const badgeBg = !isActive && !isOverdue ? PENDING_BADGE : {};

            return (
              <div className="timeline-item" key={idx}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <strong style={{ color: isActive ? "var(--text-primary)" : "var(--text-secondary)" }}>
                      {event.title}
                    </strong>
                    <span className={`badge ${badgeClass}`} style={badgeBg}>
                      {SLA_STATUS_LABEL[event.status] ?? event.status}
                    </span>
                  </div>
                  <p style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
                    {event.instructions} <strong>Deadline: {event.deadline_date}</strong>
                  </p>
                  <ExplainTrail explanation={event.explanation} lang={currentLang} />
                </div>
              </div>
            );
          })}
        </div>
      ) : loading ? (
        <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", padding: "1rem 0" }}>
          Calculating statutory SLA milestones...
        </p>
      ) : (
        <div className="timeline-list">
          <div className="timeline-item">
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong style={{ color: "var(--text-primary)" }}>{t.tier1Label}</strong>
                <span className="badge badge-info">{t.activeBadge}</span>
              </div>
              <p style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
                {t.tier1Desc.replace("{insurer}", insurerName || t.insurerName)}
              </p>
            </div>
          </div>
          <div className="timeline-item">
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong style={{ color: "var(--text-secondary)" }}>{t.tier2Label}</strong>
                <span className="badge" style={PENDING_BADGE}>{t.pendingBadge}</span>
              </div>
              <p style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
                {t.tier2Desc}
              </p>
            </div>
          </div>
          <div className="timeline-item">
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong style={{ color: "var(--text-secondary)" }}>{t.tier3Label}</strong>
                <span className="badge" style={PENDING_BADGE}>{t.pendingBadge}</span>
              </div>
              <p style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
                {t.tier3Desc}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
