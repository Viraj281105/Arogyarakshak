"use client";

import React, { useState } from "react";
import { API_BASE, caseAuthHeaders } from "../../../hooks/useApi";
import { saveBlob } from "../../../lib/download";
import { ClinicalStatementCard, ProvenanceBadge } from "../../clinical/Attribution";
import { TONE_CLASS } from "../../../lib/labels";
import type { AppealResponse } from "./types";

const warningBox: React.CSSProperties = {
  padding: "0.75rem 1rem",
  marginBottom: "1rem",
  background: "rgba(245, 158, 11, 0.08)",
  border: "1px solid rgba(245, 158, 11, 0.25)",
  borderRadius: "var(--radius-md)",
  fontSize: "0.85rem",
  color: "var(--status-warning)",
};

/** The drafted appeal letter (5-agent pipeline, #18/#66), the attributed human clinical
 *  annex (ADR-011) and the signed-PDF download. */
export function AppealLetterCard({ appealData, caseId, caseToken }: { appealData: AppealResponse; caseId: string; caseToken?: string }) {
  const [downloadError, setDownloadError] = useState<string | null>(null);

  // Downloads the exact signed PDF the appeal drafted (#66) — served from stored
  // bytes, never regenerated, so it always matches what was hashed and signed.
  const handleDownloadAppealPdf = async () => {
    setDownloadError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/billnyay/cases/${caseId}/appeal/pdf`, {
        headers: caseAuthHeaders(caseToken),
      });
      if (!res.ok) {
        setDownloadError(`Could not download the appeal PDF (HTTP ${res.status}).`);
        return;
      }
      saveBlob(await res.blob(), `appeal_${caseId}.pdf`);
    } catch {
      setDownloadError("Could not download the appeal PDF. Is the backend reachable?");
    }
  };

  return (
    <div
      style={{
        background: "var(--bg-base)",
        padding: "1.25rem",
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--border-subtle)",
        marginBottom: "1.5rem",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
        <h3>📝 Appeal Letter Drafted</h3>
        <span style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
          <ProvenanceBadge provenance="AI_DERIVED" />
          {/* "Judge" is an automated scoring agent — never shown as a human or legal approval. */}
          <span className={appealData.status === "approve" ? TONE_CLASS.neutral : TONE_CLASS.warning}>
            {appealData.status === "approve" ? "Passed automated quality check" : "Automated check suggests revision"}
          </span>
        </span>
      </div>
      <p style={{ fontSize: "0.8rem", opacity: 0.85, marginTop: "-0.5rem" }}>
        This letter is drafted by software. It is not legal advice and not a clinician&apos;s opinion; review it before sending.
      </p>

      {!appealData.llm_backed && (
        <div style={warningBox}>
          ⓘ Offline template: no AI backend is configured, so this is a static statutory draft, not a
          case-specific analysis. Review carefully before sending.
        </div>
      )}
      {!appealData.denial_facts_extracted && (
        <div style={warningBox}>
          ⓘ Denial details could not be extracted from your document. Fill in the denial code, insurer
          reason, and policy clause yourself before sending.
        </div>
      )}

      <pre
        style={{
          whiteSpace: "pre-wrap",
          fontFamily: "inherit",
          fontSize: "0.875rem",
          lineHeight: 1.6,
          color: "var(--text-primary)",
          marginBottom: "1.25rem",
        }}
      >
        {appealData.appeal_letter}
      </pre>

      {/* ADR-011: the human clinical annex is appended verbatim; when absent, say so. */}
      <div style={{ marginBottom: "1.25rem" }}>
        <h4 style={{ marginBottom: "0.5rem" }}>Attributed clinical statement</h4>
        {appealData.human_clinical_statement_attached ? (
          appealData.clinical_statements.map((s) => <ClinicalStatementCard key={s.statement_id} statement={s} />)
        ) : (
          <p style={{ fontSize: "0.85rem", color: "var(--status-warning)" }}>
            No statement from a named clinician is attached. Any clinical reasoning in the letter above is general,
            software-drafted reasoning — not a doctor&apos;s opinion. Use &ldquo;Request Clinical Review&rdquo; to get one.
            (This note is for you only; it is not printed in the PDF.)
          </p>
        )}
        <p style={{ fontSize: "0.75rem", opacity: 0.8 }}>
          The downloadable PDF is re-generated whenever a clinician finalizes, withdraws or you cancel a statement, so
          always download it again right before sending. An older copy will fail integrity verification.
        </p>
      </div>

      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => navigator.clipboard.writeText(`${appealData.appeal_letter}\n\n${appealData.clinical_annex}`)}
        >
          📋 Copy Appeal Letter
        </button>
        <button type="button" className="btn btn-primary" onClick={handleDownloadAppealPdf}>
          📥 Download Signed Appeal PDF
        </button>
      </div>
      {downloadError && (
        <p style={{ color: "#ef4444", fontSize: "0.85rem", marginTop: "0.5rem" }}>⚠️ {downloadError}</p>
      )}
    </div>
  );
}
