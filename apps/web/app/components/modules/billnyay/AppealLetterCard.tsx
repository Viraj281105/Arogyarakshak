"use client";

import React, { useState } from "react";
import { caseAuthHeaders } from "../../../hooks/useApi";
import { saveBlob } from "../../../lib/download";
import { ClinicalStatementCard, ProvenanceBadge } from "../../clinical/Attribution";
import { TONE_CLASS } from "../../../lib/labels";
import { StatePanel } from "../../clinical/StatePanel";
import type { AppealResponse } from "./types";
import { apiFetch } from "../../../lib/apiFetch";
import { useT } from "../../../i18n/useT";

/** The drafted appeal letter (5-agent pipeline, #18/#66), the attributed human clinical
 *  annex (ADR-011) and the signed-PDF download. */
export function AppealLetterCard({ appealData, caseId, caseToken }: { appealData: AppealResponse; caseId: string; caseToken?: string }) {
  const tr = useT();
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(`${appealData.appeal_letter}

${appealData.clinical_annex}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setDownloadError(tr("Could not copy to the clipboard. Select the letter text and copy it instead."));
    }
  };

  // Downloads the exact signed PDF the appeal drafted (#66) — served from stored
  // bytes, never regenerated, so it always matches what was hashed and signed.
  const handleDownloadAppealPdf = async () => {
    setDownloadError(null);
    try {
      const res = await apiFetch(`/api/v1/billnyay/cases/${caseId}/appeal/pdf`, {
        headers: caseAuthHeaders(caseToken),
      });
      if (!res.ok) {
        setDownloadError(tr("Could not download the appeal PDF (HTTP {status}).", { status: res.status }));
        return;
      }
      saveBlob(await res.blob(), `appeal_${caseId}.pdf`);
    } catch {
      setDownloadError(tr("Could not download the appeal PDF. Is the backend reachable?"));
    }
  };

  return (
    <section className="case-panel bn-card bn-appeal" aria-labelledby="bn-appeal-title">
      <div className="case-panel-head">
        <h3 id="bn-appeal-title">{tr("Appeal letter draft")}</h3>
        <span className="bn-badges">
          <ProvenanceBadge provenance="AI_DERIVED" />
          {/* "Judge" is an automated scoring agent — never shown as a human or legal approval. */}
          <span className={appealData.status === "approve" ? TONE_CLASS.neutral : TONE_CLASS.warning}>
            {appealData.status === "approve" ? tr("Passed automated quality check") : tr("Automated check suggests revision")}
          </span>
        </span>
      </div>
      <p className="bn-fine">{tr("This letter is drafted by software. It is not legal advice and not a clinician's opinion; review it before sending.")}</p>

      {!appealData.llm_backed && (
        <div className="bn-notice is-warning" role="note">{tr("Offline template: no AI backend is configured, so this is a static statutory draft, not a case-specific analysis. Review carefully before sending.")}</div>
      )}
      {!appealData.denial_facts_extracted && (
        <div className="bn-notice is-warning" role="note">{tr("Denial details could not be extracted from your document. Fill in the denial code, insurer reason, and policy clause yourself before sending.")}</div>
      )}

      <article className="bn-letter" aria-label={tr("Drafted appeal letter")}>
        <pre tabIndex={0}>{appealData.appeal_letter}</pre>
      </article>

      {/* ADR-011: the human clinical annex is appended verbatim; when absent, say so. */}
      <div className="bn-annex">
        <h4>{tr("Attributed clinical statement")}</h4>
        {appealData.human_clinical_statement_attached ? (
          appealData.clinical_statements.map((s) => <ClinicalStatementCard key={s.statement_id} statement={s} />)
        ) : (
          <p className="bn-annex-missing">{tr("No statement from a named clinician is attached. Any clinical reasoning in the letter above is general, software-drafted reasoning — not a doctor's opinion. Use “Request Clinical Review” to get one. (This note is for you only; it is not printed in the PDF.)")}</p>
        )}
        <p className="bn-fine">{tr("The downloadable PDF is re-generated whenever a clinician finalizes, withdraws or you cancel a statement, so always download it again right before sending. An older copy will fail integrity verification.")}</p>
      </div>

      <div className="bn-actions-row">
        <button type="button" className="btn btn-primary" onClick={handleDownloadAppealPdf}>
          <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
            <path d="M12 4v11M7 10l5 5 5-5M5 20h14" />
          </svg>{tr("Download signed appeal PDF")}</button>
        <button type="button" className="btn btn-ghost" onClick={() => void handleCopy()}>
          <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
            <path d="M8 8h11v12H8zM5 16V4h11" />
          </svg>
          {copied ? tr("Copied") : tr("Copy letter text")}
        </button>
      </div>
      {downloadError && <StatePanel kind="error">{downloadError}</StatePanel>}
    </section>
  );
}
