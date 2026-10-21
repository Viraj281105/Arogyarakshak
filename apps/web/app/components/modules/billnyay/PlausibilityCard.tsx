"use client";

import React from "react";
import { ProvenanceBadge } from "../../clinical/Attribution";
import { StatePanel } from "../../clinical/StatePanel";
import { TONE_CLASS, humanizeEnum } from "../../../lib/labels";
import type { PlausibilityResponse } from "./types";

/** Clinical plausibility (ADR-011) — machine-derived, bounded, not a necessity verdict. */
export function PlausibilityCard({ data }: { data: PlausibilityResponse }) {
  return (
    <div
      style={{
        padding: "1rem 1.25rem",
        marginBottom: "1.5rem",
        border: "1px solid var(--border-medium)",
        borderRadius: "var(--radius-md)",
      }}
    >
      <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap", marginBottom: "0.5rem" }}>
        <h3 style={{ margin: 0 }}>Clinical plausibility check</h3>
        <ProvenanceBadge provenance="AI_DERIVED" />
        <span
          className={
            data.assessment.status === "PLAUSIBLE"
              ? TONE_CLASS.success
              : data.assessment.status === "POTENTIAL_INCONSISTENCY"
              ? TONE_CLASS.danger
              : TONE_CLASS.warning
          }
        >
          {humanizeEnum(data.assessment.status)}
        </span>
        {data.clinical_review.required && data.assessment.status !== "CLINICAL_REVIEW_RECOMMENDED" && (
          <span className={TONE_CLASS.warning}>Clinical review recommended</span>
        )}
        <span className={TONE_CLASS.neutral} title="How much of the bill the curated reference could assess">
          {humanizeEnum(data.assessment.coverage)}
        </span>
      </div>
      {data.safety_check?.status === "UNAVAILABLE" && (
        <StatePanel kind="warning">
          <strong>Safety check unavailable.</strong> The clinical safety rules could not be evaluated for this case, so no
          safety assessment was made — this is not the same as &quot;no escalation&quot;.
        </StatePanel>
      )}
      <p style={{ fontSize: "0.9rem" }}>{data.assessment.summary}</p>
      <p style={{ fontSize: "0.8rem" }}>
        Evidence used:{" "}
        {data.assessment.evidence_used.map((e) => `${humanizeEnum(e.kind)}: ${e.value}`).join("; ") || "none"}
      </p>
      {data.assessment.references.map((r) => (
        <p key={r.icd10_code} style={{ fontSize: "0.75rem", opacity: 0.85 }}>
          Reference: {r.name} (project-curated table, {r.version} — not a published clinical guideline) — {r.icd10_code}{" "}
          {r.diagnosis_label}
        </p>
      ))}
      {(data.assessment.conflicting_items ?? []).length > 0 && (
        <p style={{ fontSize: "0.8rem", color: "var(--status-danger)" }}>
          Expected for a diagnosis that is not documented: {(data.assessment.conflicting_items ?? []).join(", ")}
        </p>
      )}
      {data.assessment.not_assessed_items.length > 0 && (
        <p style={{ fontSize: "0.8rem", color: "var(--status-warning)" }}>
          Not assessed (outside the reference): {data.assessment.not_assessed_items.join(", ")}
        </p>
      )}
      {data.assessment.excluded_administrative_items.length > 0 && (
        <p style={{ fontSize: "0.75rem", opacity: 0.85 }}>
          Set aside as administrative charges, not interventions:{" "}
          {data.assessment.excluded_administrative_items.join(", ")}
        </p>
      )}
      <p style={{ fontSize: "0.75rem", opacity: 0.85 }}>{data.assessment.guideline_note}</p>
      <p style={{ fontSize: "0.75rem", fontWeight: 600 }}>{data.assessment.disclaimer}</p>
    </div>
  );
}
