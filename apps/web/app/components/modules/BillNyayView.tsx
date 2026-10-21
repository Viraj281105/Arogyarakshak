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

  const showExample = !hasRun && !caseId;

  return (
    <div className="card">
      <div style={{ marginBottom: "1.5rem" }}>
        <h2>{t.title}</h2>
        <p>{t.desc}</p>
      </div>

      {/* Action Buttons */}
      {caseId && (
        <div style={{ marginBottom: "1.5rem", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button
            type="button"
            className="btn btn-primary"
            style={{ flex: 1, minWidth: "220px" }}
            onClick={handleRunAudit}
            disabled={api.loading}
          >
            {api.loading ? (
              <>
                <span className="step-indicator active" style={{ display: "inline-block", marginRight: "0.25rem" }} />
                Auditing bill against CGHS benchmarks...
              </>
            ) : (
              <>⚖️ Run CGHS Benchmark Audit</>
            )}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ flex: 1, minWidth: "220px" }}
            onClick={handleDraftAppeal}
            disabled={appealApi.loading}
          >
            {appealApi.loading ? (
              <>
                <span className="step-indicator active" style={{ display: "inline-block", marginRight: "0.25rem" }} />
                Running 5-agent appeal pipeline...
              </>
            ) : (
              <>📝 Draft IRDAI Appeal Letter</>
            )}
          </button>
          <button
            type="button"
            className="btn"
            style={{ flex: 1, minWidth: "220px", border: "1px solid var(--border-medium)" }}
            onClick={handleCheckPlausibility}
            disabled={plausibilityApi.loading}
          >
            {plausibilityApi.loading ? "Checking plausibility…" : "🩺 Check clinical plausibility"}
          </button>
        </div>
      )}

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

      {/* No Case Active Prompt */}
      {!caseId && !hasRun && (
        <div
          style={{
            padding: "1.25rem",
            marginBottom: "1.5rem",
            background: "rgba(6, 182, 212, 0.06)",
            border: "1px solid rgba(6, 182, 212, 0.2)",
            borderRadius: "var(--radius-md)",
            textAlign: "center",
            color: "var(--text-secondary)",
            fontSize: "0.9rem",
          }}
        >
          📤 Upload a hospital bill above to run a live CGHS benchmark audit.
        </div>
      )}

      {/* Error State */}
      {api.error && (
        <div
          style={{
            padding: "1rem",
            marginBottom: "1.5rem",
            background: "rgba(239, 68, 68, 0.15)",
            border: "1px solid var(--status-danger)",
            borderRadius: "var(--radius-md)",
            color: "#fca5a5",
            fontSize: "0.9rem",
          }}
        >
          ⚠️ {api.error}
        </div>
      )}

      {appealApi.loading && <StatePanel kind="loading">Drafting the appeal letter and signing the PDF…</StatePanel>}
      {appealApi.error && (
        <StatePanel kind="error" onRetry={handleDraftAppeal}>
          Could not draft the appeal: {appealApi.error}
        </StatePanel>
      )}

      {/* Appeal Letter (5-agent pipeline, #18/#66) */}
      {appealApi.data && caseId && <AppealLetterCard appealData={appealApi.data} caseId={caseId} caseToken={caseToken} />}

      {/* Real Audit Results */}
      {api.data && <AuditResults audit={api.data} currentLang={currentLang} />}

      {/* Before any case: say what to do. No invented example figures — a judge (or a
          patient) could otherwise mistake them for an audit result. */}
      {showExample && (
        <div
          style={{
            padding: "0.85rem 1rem",
            border: "1px dashed var(--border-subtle)",
            borderRadius: "var(--radius-md)",
            fontSize: "0.85rem",
            color: "var(--text-secondary)",
          }}
        >
          Upload a hospital bill above (or add its discharge summary to the same case) to compare each line with the
          CGHS reference rates. Lines with no matching reference rate are listed as not benchmarked — never as fair or
          overcharged.
        </div>
      )}
    </div>
  );
};
