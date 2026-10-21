"use client";

import React from "react";
import { useApi, caseAuthHeaders } from "../../../hooks/useApi";
import { ClinicalStatementCard, ProvenanceBadge } from "../../clinical/Attribution";
import { ClinicalReviewPanel } from "../../clinical/ClinicalReviewPanel";
import type { ClinicalStatementsResponse, DisputeAuditResult } from "./types";

/** ADR-011 for a denial: the machine-derived "clinical review required" trigger, the
 *  request for a named clinician's statement, and attaching finalized statements. */
export function ClinicalSection({
  result,
  caseId,
  caseToken,
  insurerName,
}: {
  result: DisputeAuditResult;
  caseId?: string;
  caseToken?: string;
  insurerName: string;
}) {
  const statementsApi = useApi<ClinicalStatementsResponse>();

  const loadClinicalStatements = async () => {
    if (!caseId) return;
    await statementsApi.execute(`/api/v1/bimanyay/cases/${encodeURIComponent(caseId)}/clinical-statements`, {
      method: "GET",
      headers: caseAuthHeaders(caseToken),
    });
  };

  return (
    <>
      {/* ADR-011: clinical-interpretation trigger (machine-derived) */}
      {result.clinical_review?.requires_clinical_interpretation && (
        <div className="bm-clinical-flag" role="note">
          <div className="bn-badges">
            <strong>Clinical review required</strong>
            <ProvenanceBadge provenance="AI_DERIVED" />
          </div>
          <ul className="safety-limits">
            {result.clinical_review.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          <p className="bn-fine">{result.clinical_review.note}</p>
          {!caseId && (
            <p className="bn-fine">
              Upload your records above to create a case, then request a statement from a named doctor here.
            </p>
          )}
        </div>
      )}
      {caseId && (
        <ClinicalReviewPanel
          caseId={caseId}
          caseToken={caseToken}
          sourceModule="bimanyay"
          trigger={result.clinical_review?.requires_clinical_interpretation ? "DENIAL_CATEGORY" : "MANUAL"}
          recommendationReason={result.clinical_review?.reasons.join(" ") || null}
          suggestedQuestion={result.clinical_review?.suggested_clinical_question}
          insurerName={insurerName}
        />
      )}
      {caseId && (
        <div className="bm-annex">
          <button type="button" className="btn btn-secondary" onClick={loadClinicalStatements} disabled={statementsApi.loading}>
            Attach finalized clinician statements to these appeals
          </button>
          {statementsApi.data &&
            (statementsApi.data.human_clinical_statement_attached ? (
              <div className="bm-annex-list">
                {statementsApi.data.statements.map((s) => (
                  <ClinicalStatementCard key={s.statement_id} statement={s} />
                ))}
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => navigator.clipboard.writeText(statementsApi.data!.annex_text).catch(() => undefined)}
                >
                  Copy attributed annex (verbatim)
                </button>
              </div>
            ) : (
              <p className="bn-annex-missing">
                No finalized statement from a named clinician exists for this case. Do not describe any appeal
                reasoning as a doctor&apos;s opinion.
              </p>
            ))}
          {statementsApi.error && <p className="ds-hint">Could not load clinician statements: {statementsApi.error}</p>}
        </div>
      )}
    </>
  );
}
