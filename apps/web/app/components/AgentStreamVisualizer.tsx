"use client";

import React from "react";
import { Language, translations } from "../translations";

export type PipelineStep = 0 | 1 | 2 | 3 | 4;

interface AgentStreamVisualizerProps {
  currentLang: Language;
  currentStep: PipelineStep;
  activeFileName?: string;
  caseId?: string;
  liveLog?: string;
}

/**
 * Where the document is in processing, driven only by the server's status stream
 * (useCaseSession). The active stage shows an indeterminate bar: the stream reports which
 * stage is running, not how far through it is, so no percentage is shown.
 */
export const AgentStreamVisualizer: React.FC<AgentStreamVisualizerProps> = ({ currentLang, currentStep, liveLog }) => {
  const t = translations[currentLang];
  const complete = currentStep >= 4;

  const steps = [
    { id: 1, label: t.stream.stepOcr },
    { id: 2, label: t.stream.stepEntities },
    { id: 3, label: t.stream.stepAudit },
    { id: 4, label: t.stream.stepComplete },
  ];

  return (
    <section className="case-panel tracker" aria-label="Document processing progress">
      <div className="case-panel-head">
        <h3>{t.stream.statusHeading}</h3>
        <span className={`tracker-count ${complete ? "is-complete" : ""}`} aria-live="polite">
          {complete ? "Complete" : `Stage ${currentStep} of 4`}
        </span>
      </div>

      <ol className="tracker-rail">
        {steps.map((s) => {
          const done = currentStep > s.id || complete;
          const active = !complete && currentStep === s.id;
          const state = done ? "is-done" : active ? "is-active" : "is-pending";
          return (
            <li key={s.id} className={`tracker-step ${state}`} aria-current={active ? "step" : undefined}>
              <span className="tracker-node" aria-hidden="true">
                {done ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" className="lp-icon">
                    <path d="M5 12.5l4.2 4.2L19 7" />
                  </svg>
                ) : (
                  <span>{s.id}</span>
                )}
              </span>
              <span className="tracker-label">
                {s.label}
                <span className="sr-only">{done ? " — done" : active ? " — in progress" : " — waiting"}</span>
              </span>
              <span className="tracker-bar" aria-hidden="true" />
            </li>
          );
        })}
      </ol>

      {liveLog && (
        <p className="tracker-log" aria-live="polite">
          <span className="tracker-log-label">Latest from the server</span>
          <span className="tracker-log-text">{liveLog}</span>
        </p>
      )}
    </section>
  );
};
