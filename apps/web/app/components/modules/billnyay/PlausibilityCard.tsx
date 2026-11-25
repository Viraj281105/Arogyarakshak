"use client";

import React from "react";
import { ProvenanceBadge } from "../../clinical/Attribution";
import { StatePanel } from "../../clinical/StatePanel";
import { TONE_CLASS, humanizeEnum } from "../../../lib/labels";
import type { PlausibilityResponse } from "./types";
import { useT } from "../../../i18n/useT";

/** Clinical plausibility (ADR-011) — machine-derived, bounded, not a necessity verdict. */
export function PlausibilityCard({ data }: { data: PlausibilityResponse }) {
  const tr = useT();
  const a = data.assessment;
  const conflicting = a.conflicting_items ?? [];
  const tone = a.status === "PLAUSIBLE" ? "success" : a.status === "POTENTIAL_INCONSISTENCY" ? "danger" : "warning";
  return (
    <section className="case-panel bn-card" aria-labelledby="bn-plausibility-title">
      <div className="case-panel-head">
        <h3 id="bn-plausibility-title">{tr("Clinical plausibility check")}</h3>
        <ProvenanceBadge provenance="AI_DERIVED" />
      </div>
      <div className="bn-badges">
        <span className={TONE_CLASS[tone]}>{tr(humanizeEnum(a.status))}</span>
        {data.clinical_review.required && a.status !== "CLINICAL_REVIEW_RECOMMENDED" && (
          <span className={TONE_CLASS.warning}>{tr("Clinical review recommended")}</span>
        )}
        <span className={TONE_CLASS.neutral} title={tr("How much of the bill the curated reference could assess")}>
          {tr(humanizeEnum(a.coverage))}
        </span>
      </div>
      {data.safety_check?.status === "UNAVAILABLE" && (
        <StatePanel kind="warning">
          <strong>{tr("Safety check unavailable.")}</strong>{" "}{tr("The clinical safety rules could not be evaluated for this case, so no safety assessment was made — this is not the same as \"no escalation\".")}</StatePanel>
      )}
      <p className="bn-summary">{a.summary}</p>

      <dl className="bn-facts">
        <div>
          <dt>{tr("Evidence used")}</dt>
          <dd>{a.evidence_used.map((e) => `${tr(humanizeEnum(e.kind))}: ${e.value}`).join("; ") || tr("none")}</dd>
        </div>
        {conflicting.length > 0 && (
          <div className="is-danger">
            <dt>{tr("Expected for a diagnosis that is not documented")}</dt>
            <dd>{conflicting.join(", ")}</dd>
          </div>
        )}
        {a.not_assessed_items.length > 0 && (
          <div className="is-warning">
            <dt>{tr("Not assessed (outside the reference)")}</dt>
            <dd>{a.not_assessed_items.join(", ")}</dd>
          </div>
        )}
        {a.excluded_administrative_items.length > 0 && (
          <div>
            <dt>{tr("Set aside as administrative charges, not interventions")}</dt>
            <dd>{a.excluded_administrative_items.join(", ")}</dd>
          </div>
        )}
      </dl>

      {a.references.map((r) => (
        <p key={r.icd10_code} className="bn-fine">{tr("Reference: {name} (project-curated table, {version} — not a published clinical guideline) — {icd10_code} {diagnosis_label}", { name: r.name, version: r.version, icd10_code: r.icd10_code, diagnosis_label: r.diagnosis_label })}</p>
      ))}
      <p className="bn-fine">{a.guideline_note}</p>
      <p className="bn-fine bn-disclaimer">{data.assessment.disclaimer}</p>
    </section>
  );
}
