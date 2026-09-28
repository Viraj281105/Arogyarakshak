"use client";

import React from "react";
import { ClinicalStatement, PROVENANCE_LABELS, Provenance, ReviewerProfile, ReviewerSnapshot } from "../../lib/clinical";
import { TONE_CLASS, Tone, formatTimestamp, humanizeEnum, verificationTone } from "../../lib/labels";

// Machine-derived, human-reviewed and human-authored must never look alike.
const PROVENANCE_TONE: Record<Provenance, Tone> = {
  AI_DERIVED: "machine",
  HUMAN_REVIEWED: "human-reviewed",
  HUMAN_AUTHORED: "human-authored",
  EXTERNAL_SOURCE: "warning",
  PATIENT_PROVIDED: "warning",
};

const PROVENANCE_ICON: Record<Provenance, string> = {
  AI_DERIVED: "⚙",
  HUMAN_REVIEWED: "👁",
  HUMAN_AUTHORED: "✍",
  EXTERNAL_SOURCE: "↗",
  PATIENT_PROVIDED: "🧾",
};

export const ProvenanceBadge: React.FC<{ provenance: Provenance | null | undefined }> = ({ provenance }) =>
  provenance ? (
    <span className={TONE_CLASS[PROVENANCE_TONE[provenance]]} title={`Provenance: ${PROVENANCE_LABELS[provenance]}`}>
      <span aria-hidden="true">{PROVENANCE_ICON[provenance]} </span>
      {PROVENANCE_LABELS[provenance]}
    </span>
  ) : null;

/** The server's verification label, verbatim, in a tone that never upgrades it. */
export const VerificationBadge: React.FC<{ status: string; label: string }> = ({ status, label }) => (
  <span className={TONE_CLASS[verificationTone(status)]} title="What ArogyaRakshak actually knows about this registration">
    {label}
  </span>
);

/**
 * Who the reviewer is, as far as ArogyaRakshak actually knows. The verification wording is
 * the server's `verification_label` verbatim — the client never upgrades it.
 */
export const ReviewerAttribution: React.FC<{
  reviewer: ReviewerProfile | ReviewerSnapshot | null;
  coiLabel?: string | null;
  coiDisclosure?: string | null;
}> = ({ reviewer, coiLabel, coiDisclosure }) => {
  if (!reviewer) return null;
  return (
    <div style={{ fontSize: "0.85rem", lineHeight: 1.6 }}>
      <div>
        <strong>{reviewer.name}</strong>
        {reviewer.designation ? ` · ${reviewer.designation}` : ""} · {reviewer.category_label}
        {reviewer.specialty ? ` · ${reviewer.specialty}` : ""}
      </div>
      {reviewer.registration_number && (
        <div>
          Registration: {reviewer.registration_number}
          {reviewer.registration_authority ? ` (${reviewer.registration_authority})` : ""}
        </div>
      )}
      <div>
        <VerificationBadge status={reviewer.verification_status} label={reviewer.verification_label} />
      </div>
      {coiLabel && (
        <div style={{ marginTop: "0.35rem" }}>
          <strong>Conflict of interest:</strong> {coiLabel}
          {coiDisclosure ? ` — ${coiDisclosure}` : ""}
        </div>
      )}
    </div>
  );
};

export const ClinicalStatementCard: React.FC<{ statement: ClinicalStatement }> = ({ statement }) => {
  const current = statement.status === "FINALIZED";
  return (
    <article
      style={{
        border: `1px solid ${current ? "var(--status-success)" : "var(--border-subtle)"}`,
        borderRadius: "var(--radius-md)",
        padding: "1rem",
        marginBottom: "0.75rem",
        opacity: current ? 1 : 0.75,
      }}
    >
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center", marginBottom: "0.5rem" }}>
        <ProvenanceBadge provenance={statement.provenance} />
        <span className={`badge ${current ? "badge-success" : "badge-info"}`}>
          Version {statement.statement_version} · {humanizeEnum(statement.status)}
        </span>
      </div>
      <ReviewerAttribution
        reviewer={statement.reviewer_snapshot}
        coiLabel={statement.coi_label}
        coiDisclosure={statement.coi_disclosure}
      />
      <div style={{ marginTop: "0.75rem", fontSize: "0.85rem" }}>
        <div className="stat-label">Question put to the reviewer</div>
        <p style={{ marginBottom: "0.5rem" }}>{statement.clinical_question}</p>
        <div className="stat-label">Reviewer&apos;s own statement (verbatim)</div>
        <blockquote
          style={{ whiteSpace: "pre-wrap", borderLeft: "3px solid var(--brand-cyan)", paddingLeft: "0.75rem", margin: "0.25rem 0 0.75rem" }}
        >
          {statement.reviewer_statement}
        </blockquote>
        <div className="stat-label">Limitations stated by the reviewer</div>
        <p style={{ whiteSpace: "pre-wrap", marginBottom: "0.5rem" }}>{statement.limitations}</p>
        <div className="stat-label">Evidence the reviewer confirmed reviewing</div>
        <ul style={{ paddingLeft: "1.1rem", marginBottom: "0.5rem" }}>
          {statement.evidence_reviewed.map((e) => (
            <li key={e.item_id}>
              {e.label} <ProvenanceBadge provenance={e.provenance} />
            </li>
          ))}
        </ul>
        {statement.withdrawn_reason && (
          <p style={{ color: "var(--status-warning)" }}>Withdrawn by the reviewer: {statement.withdrawn_reason}</p>
        )}
        <p style={{ fontSize: "0.75rem", opacity: 0.75 }}>
          This is the named reviewer&apos;s own professional opinion. It is not an insurer determination and not a
          finding of ArogyaRakshak.
          {statement.finalized_at ? ` Finalized ${formatTimestamp(statement.finalized_at)}.` : ""}
          {statement.content_sha256 ? ` SHA-256 ${statement.content_sha256.slice(0, 16)}…` : ""}
        </p>
      </div>
    </article>
  );
};
