"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";
import { useApi, caseAuthHeaders } from "../../hooks/useApi";
import { clinicalPaths } from "../../lib/clinical";
import { ClinicalReviewPanel } from "../clinical/ClinicalReviewPanel";
import { StatePanel } from "../clinical/StatePanel";
import { AppealLetterCard } from "./billnyay/AppealLetterCard";
import { AuditResults } from "./billnyay/AuditResults";
import { PlausibilityCard } from "./billnyay/PlausibilityCard";
import type { AppealResponse, AuditResponse, PlausibilityResponse } from "./billnyay/types";

interface BillNyayViewProps {
  currentLang: Language;
  caseId?: string;
  caseToken?: string;
}

/** BillNyay: CGHS bill audit, the 5-agent appeal draft, and the bounded clinical
 *  plausibility check with an optional named-clinician review. */
export const BillNyayView: React.FC<BillNyayViewProps> = ({ currentLang, caseId, caseToken }) => {
  const t = translations[currentLang].modules.billnyay;
  const api = useApi<AuditResponse>();
  const appealApi = useApi<AppealResponse>();
  const plausibilityApi = useApi<PlausibilityResponse>();
  const [hasRun, setHasRun] = useState(false);

  const handleCheckPlausibility = async () => {
    if (!caseId) return;
    await plausibilityApi.execute(clinicalPaths.plausibility(caseId), {
      method: "GET",
      headers: caseAuthHeaders(caseToken),
    });
  };

  const handleRunAudit = async () => {
    if (!caseId) return;
    setHasRun(true);
    await api.execute(`/api/v1/billnyay/cases/${caseId}/audit`, {
      headers: caseAuthHeaders(caseToken),
    });
  };

  // Runs the 5-agent appeal pipeline (#18) — does not require a prior audit call,
  // since it reads the case's document text directly.
  const handleDraftAppeal = async () => {
    if (!caseId) return;
    await appealApi.execute(`/api/v1/billnyay/cases/${caseId}/appeal?language=${currentLang}`, {
      headers: caseAuthHeaders(caseToken),
    });
  };

  return (
    <div className="module-panel">
      <header className="module-head">
        <p className="lp-kicker">BillNyay · compared with CGHS 2024 rates</p>
        <h2>{t.title}</h2>
        <p>{t.desc}</p>
      </header>

      {/* Action Buttons */}
      {caseId && (
        <div className="bn-tools" role="group" aria-label="BillNyay checks">
          <button type="button" className="bn-tool is-primary" onClick={handleRunAudit} disabled={api.loading}>
            <span className="bn-tool-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" className="lp-icon">
                <path d="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6M9 16h3" />
              </svg>
            </span>
            <span className="bn-tool-text">
              <strong>{api.loading ? "Comparing with CGHS rates…" : api.data ? "Run the CGHS audit again" : "Run the CGHS audit"}</strong>
              <span>Each bill line against the CGHS reference rows.</span>
            </span>
            {api.loading && <span className="spinner" aria-hidden="true" />}
          </button>
          <button type="button" className="bn-tool" onClick={handleDraftAppeal} disabled={appealApi.loading}>
            <span className="bn-tool-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" className="lp-icon">
                <path d="M5 4h10l4 4v12H5zM9 12h6M9 16h4M15 4v4h4" />
              </svg>
            </span>
            <span className="bn-tool-text">
              <strong>{appealApi.loading ? "Drafting the appeal…" : "Draft an appeal letter"}</strong>
              <span>From your document text — you review it before sending.</span>
            </span>
            {appealApi.loading && <span className="spinner" aria-hidden="true" />}
          </button>
          <button type="button" className="bn-tool" onClick={handleCheckPlausibility} disabled={plausibilityApi.loading}>
            <span className="bn-tool-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" className="lp-icon">
                <path d="M6 3v6a4 4 0 0 0 8 0V3M10 13v3a5 5 0 0 0 10 0v-2M20 12a2 2 0 1 0 0-.01" />
              </svg>
            </span>
            <span className="bn-tool-text">
              <strong>{plausibilityApi.loading ? "Checking plausibility…" : "Check clinical plausibility"}</strong>
              <span>Do the billed interventions fit the documented diagnosis?</span>
            </span>
            {plausibilityApi.loading && <span className="spinner" aria-hidden="true" />}
          </button>
        </div>
      )}

      {/* Before any case: say what to do. No invented example figures — a judge (or a
          patient) could otherwise mistake them for an audit result. */}
      {!caseId && (
        <div className="module-empty">
          <span className="module-empty-icon" aria-hidden="true">
            <svg width="26" height="26" viewBox="0 0 24 24" className="lp-icon">
              <path d="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6M9 16h3" />
            </svg>
          </span>
          <div>
            <strong>No document checked yet</strong>
            <p>
              Upload a hospital bill (or add its discharge summary to the same case) to compare each line with the CGHS
              reference rates. Lines with no matching reference rate are listed as not benchmarked — never as fair or
              overcharged.
            </p>
            <a href="#intake-dropzone" className="btn btn-secondary btn-compact">
              Add a document
            </a>
          </div>
        </div>
      )}

      {/* CGHS audit */}
      {api.loading && !api.data && <StatePanel kind="loading">Comparing each bill line with the CGHS reference rows…</StatePanel>}
      {api.error && (
        <StatePanel kind="error" onRetry={handleRunAudit}>
          Could not run the audit: {api.error}
        </StatePanel>
      )}
      {api.data && <AuditResults audit={api.data} currentLang={currentLang} />}
      {caseId && !hasRun && (
        <p className="module-hint">Run the CGHS audit to see every line of this bill against its reference rate.</p>
      )}

      {/* Appeal Letter (5-agent pipeline, #18/#66) */}
      {appealApi.loading && <StatePanel kind="loading">Drafting the appeal letter and signing the PDF…</StatePanel>}
      {appealApi.error && (
        <StatePanel kind="error" onRetry={handleDraftAppeal}>
          Could not draft the appeal: {appealApi.error}
        </StatePanel>
      )}
      {appealApi.data && caseId && <AppealLetterCard appealData={appealApi.data} caseId={caseId} caseToken={caseToken} />}

      {/* Clinical plausibility (ADR-011) — machine-derived, bounded, not a necessity verdict */}
      {plausibilityApi.loading && <StatePanel kind="loading">Comparing the documented diagnosis and interventions…</StatePanel>}
      {plausibilityApi.error && (
        <StatePanel kind="error" onRetry={handleCheckPlausibility}>
          Could not run the plausibility check: {plausibilityApi.error}
        </StatePanel>
      )}
      {plausibilityApi.data && <PlausibilityCard data={plausibilityApi.data} />}
      {caseId && (
        <ClinicalReviewPanel
          caseId={caseId}
          caseToken={caseToken}
          sourceModule="billnyay"
          trigger={plausibilityApi.data?.clinical_review.required ? "PLAUSIBILITY_FLAG" : "MANUAL"}
          recommendationReason={plausibilityApi.data?.assessment.review_reasons.join(" ") || null}
        />
      )}
    </div>
  );
};
