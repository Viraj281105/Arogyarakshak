"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";
import { useApi, caseAuthHeaders } from "../../hooks/useApi";
import { clinicalPaths } from "../../lib/clinical";
import { ClinicalReviewPanel } from "../clinical/ClinicalReviewPanel";
import { StatePanel } from "../clinical/StatePanel";
import { LazyModulePlan } from "../actions/LazyModulePlan";
import { AppealLetterCard } from "./billnyay/AppealLetterCard";
import { AuditResults } from "./billnyay/AuditResults";
import { PlausibilityCard } from "./billnyay/PlausibilityCard";
import type { AppealResponse, AuditResponse, PlausibilityResponse } from "./billnyay/types";
import { HospitalIllustration, MedicalRecordIllustration } from "../illustrations/Illustrations";
import { EvidenceBadge, StatusBadge } from "../ui/Badges";
import { useT } from "../../i18n/useT";
import { msg } from "../../i18n/format";

// GET /api/v1/billnyay/cases/{id}/icd-audit -> billnyay.agents.icd_audit.ICDProcedureAuditItem.
interface IcdAuditResponse {
  icd10_code: string | null;
  diagnosis_text: string;
  procedures_billed: string[];
  status: "consistent" | "mismatched" | "no_procedure_billed" | "code_not_found" | "code_not_in_reference" | string;
  reference_entry_count: number;
}

/** Plain-language reading of each backend status. Only "consistent" is a positive result; none is a verdict. */
const ICD_STATUS: Record<string, { label: string; body: string; evidence: "rule-engine" | "provisional" | "unevaluated" }> = {
  consistent: {
    label: msg("Consistent with the code"),
    body: msg("At least one billed procedure matches the procedures expected for this ICD-10 code in the reference table."),
    evidence: "rule-engine",
  },
  mismatched: {
    label: msg("Worth a human review"),
    body: msg("The code is in the reference table, but none of the billed procedures matches what it expects. This is not proof of wrong coding; ask the hospital or a doctor."),
    evidence: "provisional",
  },
  no_procedure_billed: {
    label: msg("Nothing to compare"),
    body: msg("The code is in the reference table, but no procedure was found on the bill."),
    evidence: "unevaluated",
  },
  code_not_found: {
    label: msg("No ICD-10 code found"),
    body: msg("No ICD-10 code could be read from the diagnosis, so nothing was checked."),
    evidence: "unevaluated",
  },
  code_not_in_reference: {
    label: msg("Code not covered"),
    body: msg("The code was found, but the small reference table does not cover it. This is NOT evidence of a mismatch."),
    evidence: "unevaluated",
  },
};

interface BillNyayViewProps {
  currentLang: Language;
  caseId?: string;
  caseToken?: string;
}

/** BillNyay: CGHS bill audit, the 5-agent appeal draft, and the bounded clinical
 *  plausibility check with an optional named-clinician review. */
export const BillNyayView: React.FC<BillNyayViewProps> = ({ currentLang, caseId, caseToken }) => {
  const tr = useT();
  const t = translations[currentLang].modules.billnyay;
  const api = useApi<AuditResponse>();
  const appealApi = useApi<AppealResponse>();
  const plausibilityApi = useApi<PlausibilityResponse>();
  const icdApi = useApi<IcdAuditResponse>();
  const [hasRun, setHasRun] = useState(false);

  const handleIcdAudit = async () => {
    if (!caseId) return;
    await icdApi.execute(`/api/v1/billnyay/cases/${caseId}/icd-audit`, {
      method: "GET",
      headers: caseAuthHeaders(caseToken),
    });
  };

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
      <header className="ws-mod-hero ws-mod-billnyay">
        <div className="ws-mod-hero-copy">
          <p className="lp-kicker">{tr("BillNyay · compared with CGHS 2024 rates")}</p>
          <h2>{t.title}</h2>
          <p>{t.desc}</p>
          <div className="ws-kadi-badges">
            <StatusBadge tone="neutral">{tr("Compared with CGHS reference rates")}</StatusBadge>
            <StatusBadge tone="neutral">{tr("A doctor can review the findings")}</StatusBadge>
          </div>
        </div>
        <div className="ws-mod-hero-art" aria-hidden="true">
          <HospitalIllustration size={104} />
        </div>
      </header>

      {/* Action Buttons */}
      {caseId && (
        <div className="bn-tools" role="group" aria-label={tr("BillNyay checks")}>
          <button type="button" className="bn-tool is-primary" onClick={handleRunAudit} disabled={api.loading}>
            <span className="bn-tool-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" className="lp-icon">
                <path d="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6M9 16h3" />
              </svg>
            </span>
            <span className="bn-tool-text">
              <strong>{api.loading ? tr("Comparing with CGHS rates…") : api.data ? tr("Run the CGHS audit again") : tr("Run the CGHS audit")}</strong>
              <span>{tr("Each bill line against the CGHS reference rows.")}</span>
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
              <strong>{appealApi.loading ? tr("Drafting the appeal…") : tr("Draft an appeal letter")}</strong>
              <span>{tr("From your document text — you review it before sending.")}</span>
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
              <strong>{plausibilityApi.loading ? tr("Checking plausibility…") : tr("Check clinical plausibility")}</strong>
              <span>{tr("Do the billed interventions fit the documented diagnosis?")}</span>
            </span>
            {plausibilityApi.loading && <span className="spinner" aria-hidden="true" />}
          </button>
          <button type="button" className="bn-tool" onClick={handleIcdAudit} disabled={icdApi.loading}>
            <span className="bn-tool-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" className="lp-icon">
                <path d="M4 6h16M4 12h10M4 18h7M17 15l2 2 4-4" />
              </svg>
            </span>
            <span className="bn-tool-text">
              <strong>{icdApi.loading ? tr("Checking ICD-10 coding…") : tr("Check ICD-10 procedure coding")}</strong>
              <span>{tr("Compare extracted diagnosis codes against billed procedures.")}</span>
            </span>
            {icdApi.loading && <span className="spinner" aria-hidden="true" />}
          </button>
        </div>
      )}

      {/* Before any case: say what to do. No invented example figures — a judge (or a
          patient) could otherwise mistake them for an audit result. */}
      {!caseId && (
        <div className="module-empty">
          <span className="module-empty-icon" aria-hidden="true">
            <MedicalRecordIllustration size={88} />
          </span>
          <div>
            <strong>{tr("No document checked yet")}</strong>
            <p>{tr("Upload a hospital bill (or add its discharge summary to the same case) to compare each line with the CGHS reference rates. Lines with no matching reference rate are listed as not benchmarked — never as fair or overcharged.")}</p>
            <a href="/app#intake-dropzone" className="btn btn-secondary btn-compact">{tr("Add a document")}</a>
          </div>
        </div>
      )}

      {/* CGHS audit */}
      {api.loading && !api.data && <StatePanel kind="loading">{tr("Comparing each bill line with the CGHS reference rows…")}</StatePanel>}
      {api.error && (
        <StatePanel kind="error" onRetry={handleRunAudit}>{tr("Could not run the audit: {error}", { error: api.error })}</StatePanel>
      )}
      {api.data && <AuditResults audit={api.data} currentLang={currentLang} />}
      {api.data && <LazyModulePlan module="billnyay" audit={api.data} caseId={caseId} />}
      {caseId && !hasRun && (
        <p className="module-hint">{tr("Run the CGHS audit to see every line of this bill against its reference rate.")}</p>
      )}

      {/* Appeal Letter (5-agent pipeline, #18/#66) */}
      {appealApi.loading && <StatePanel kind="loading">{tr("Drafting the appeal letter and signing the PDF…")}</StatePanel>}
      {appealApi.error && (
        <StatePanel kind="error" onRetry={handleDraftAppeal}>{tr("Could not draft the appeal: {error}", { error: appealApi.error })}</StatePanel>
      )}
      {appealApi.data && caseId && <AppealLetterCard appealData={appealApi.data} caseId={caseId} caseToken={caseToken} />}

      {/* Clinical plausibility (ADR-011) — machine-derived, bounded, not a necessity verdict */}
      {plausibilityApi.loading && <StatePanel kind="loading">{tr("Comparing the documented diagnosis and interventions…")}</StatePanel>}
      {plausibilityApi.error && (
        <StatePanel kind="error" onRetry={handleCheckPlausibility}>{tr("Could not run the plausibility check: {error}", { error: plausibilityApi.error })}</StatePanel>
      )}
      {plausibilityApi.data && <PlausibilityCard data={plausibilityApi.data} />}
      {icdApi.loading && <StatePanel kind="loading">{tr("Checking ICD-10 diagnosis and procedure consistency…")}</StatePanel>}
      {icdApi.error && (
        <StatePanel kind="error" onRetry={handleIcdAudit}>{tr("Could not run the ICD-10 check: {error}", { error: icdApi.error })}</StatePanel>
      )}
      {icdApi.data && (() => {
        const d = icdApi.data;
        const st = ICD_STATUS[d.status] ?? { label: d.status, body: msg("Status reported by the server."), evidence: "unevaluated" as const };
        return (
          <section className="case-panel bn-card" aria-labelledby="bn-icd-title">
            <div className="case-panel-head">
              <h3 id="bn-icd-title">{tr("ICD-10 procedure coding check")}</h3>
              <EvidenceBadge state={st.evidence} size="sm" />
            </div>
            <p className="bn-summary">
              <strong>{tr(st.label)}.</strong> {tr(st.body)}
            </p>
            <dl className="ws-icd-facts">
              <dt>{tr("ICD-10 code read")}</dt>
              <dd className="code-tabular">{d.icd10_code ?? tr("None found")}</dd>
              <dt>{tr("Diagnosis text")}</dt>
              <dd>{d.diagnosis_text || tr("Not recorded")}</dd>
              <dt>{tr("Procedures on the bill")}</dt>
              <dd>{d.procedures_billed.length > 0 ? d.procedures_billed.join(", ") : tr("None found")}</dd>
            </dl>
            <p className="ws-muted">{tr("Checked against a curated reference table of {reference_entry_count} ICD-10 code families. It is a consistency hint for a human to follow up, not a clinical or coding judgement.", { reference_entry_count: d.reference_entry_count })}</p>
          </section>
        );
      })()}
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
