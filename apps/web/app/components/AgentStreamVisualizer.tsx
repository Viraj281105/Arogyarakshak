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

export const AgentStreamVisualizer: React.FC<AgentStreamVisualizerProps> = ({
  currentLang,
  currentStep,
  activeFileName,
  caseId,
  liveLog,
}) => {
  const t = translations[currentLang];

  const steps = [
    { id: 1, label: t.stream.stepOcr },
    { id: 2, label: t.stream.stepEntities },
    { id: 3, label: t.stream.stepAudit },
    { id: 4, label: t.stream.stepComplete },
  ];

  return (
    <div className="stream-bar" role="region" aria-live="polite" aria-label="Pipeline Progress">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span className="step-indicator active" />
          <span style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--brand-cyan)" }}>
            {t.stream.statusHeading}
          </span>
          {activeFileName && (
            <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
              [{activeFileName}]
            </span>
          )}
          {caseId && (
            <span style={{ fontSize: "0.75rem", color: "var(--brand-teal)", background: "rgba(20, 184, 166, 0.15)", padding: "2px 6px", borderRadius: "4px" }}>
              {caseId}
            </span>
          )}
        </div>
        <span style={{ fontSize: "0.8rem", color: "var(--brand-emerald)" }}>
          {currentStep >= 4 ? "✓ Audit Completed" : `Pipeline Stage ${currentStep} of 4`}
        </span>
      </div>

      {liveLog && (
        <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.4rem", fontStyle: "italic" }}>
          📡 {liveLog}
        </div>
      )}


      <div className="stream-steps">
        {steps.map((s) => {
          const isDone = currentStep > s.id || currentStep === 4;
          const isActive = currentStep === s.id;
          return (
            <div key={s.id} className="stream-step">
              <span
                className={`step-indicator ${isDone ? "done" : isActive ? "active" : ""}`}
              />
              <span
                style={{
                  fontWeight: isActive || isDone ? 600 : 400,
                  color: isDone
                    ? "var(--brand-emerald)"
                    : isActive
                    ? "var(--text-primary)"
                    : "var(--text-muted)",
                }}
              >
                {s.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
