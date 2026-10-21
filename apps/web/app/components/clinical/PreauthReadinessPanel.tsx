"use client";

import { humanizeEnum } from "../../lib/labels";
import React, { useState } from "react";
import { API_BASE, caseAuthHeaders, normalizeErrorDetail } from "../../hooks/useApi";
import { ReviewerProfile, CaseClinicalReview, clinicalPaths, clinicalRequest } from "../../lib/clinical";
import { AssignReviewer } from "./AssignReviewer";
import { ReviewerAttribution } from "./Attribution";
import { ExplainTrail } from "../ExplainTrail";
import type { Explanation } from "../../lib/explanation";
import type { Language } from "../../translations";
import { ListenSummary } from "../ListenSummary";
import { buildReadinessSummary } from "../../lib/listenSummaries";
import { StatePanel } from "./StatePanel";

interface ReadinessItem {
  item_id: string;
  label: string;
  status:
    | "PRESENT"
    | "MISSING"
    | "NEEDS_CLINICAL_CONFIRMATION"
    | "CONFIRMED_BY_REVIEWER"
    | "REJECTED_BY_REVIEWER"
    | "REVIEWER_COULD_NOT_DETERMINE";
  evidence_strength: string | null;
  evidence: { kind: string; reference: string; provenance: string }[];
  clinical_fact: boolean;
  clinical_fact_question: string | null;
  clinical_decision: { decision: string; reviewer_name: string | null; reviewer_verification_label: string | null; coi_label: string | null } | null;
  origin: "BASELINE" | "INSTITUTION_PLAYBOOK";
  /** "Why am I seeing this?" trail (ADR-017). */
  explanation?: Explanation | null;
}

interface ReadinessResponse {
  case_id: string;
  guidance_label: string;
  items: ReadinessItem[];
  recommended_actions: string[];
  ready_to_submit: boolean;
  disclaimer: string;
  evidence_scope_note: string;
  baseline_source: string;
}

const MARK: Record<ReadinessItem["status"], string> = {
  PRESENT: "✓",
  MISSING: "✗",
  NEEDS_CLINICAL_CONFIRMATION: "?",
  CONFIRMED_BY_REVIEWER: "✓",
  REJECTED_BY_REVIEWER: "✗",
  REVIEWER_COULD_NOT_DETERMINE: "?",
};

// Visual tone per status, for the mark beside each item.
const TONE: Record<ReadinessItem["status"], "ok" | "missing" | "question"> = {
  PRESENT: "ok",
  MISSING: "missing",
  NEEDS_CLINICAL_CONFIRMATION: "question",
  CONFIRMED_BY_REVIEWER: "ok",
  REJECTED_BY_REVIEWER: "missing",
  REVIEWER_COULD_NOT_DETERMINE: "question",
};

const STATUS_TEXT: Record<ReadinessItem["status"], string> = {
  PRESENT: "found in your documents",
  MISSING: "not found in the text ArogyaRakshak keeps (see below)",
  NEEDS_CLINICAL_CONFIRMATION: "clinical fact — needs a doctor's confirmation",
  CONFIRMED_BY_REVIEWER: "confirmed by a named reviewer",
  REJECTED_BY_REVIEWER: "a reviewer did NOT confirm this",
  REVIEWER_COULD_NOT_DETERMINE: "reviewer could not determine this from the records",
};

/**
 * DaaviSetu preauth readiness: documentation completeness only. It never predicts approval
 * and never marks a clinical fact satisfied without a named reviewer's decision.
 */
export const PreauthReadinessPanel: React.FC<{ caseId: string; caseToken?: string; lang?: Language }> = ({ caseId, caseToken, lang = "en" }) => {
  const [report, setReport] = useState<ReadinessResponse | null>(null);
  const [playbookId, setPlaybookId] = useState("");
  const [institutionToken, setInstitutionToken] = useState("");
  const [shareConsent, setShareConsent] = useState(false);
  const [factReview, setFactReview] = useState<CaseClinicalReview | null>(null);
  const [doctors, setDoctors] = useState<ReviewerProfile[]>([]);
  const [error, setError] = useState<string | null>(null);

  const post = async <T,>(path: string, body: unknown): Promise<T> => {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...caseAuthHeaders(caseToken),
        ...(institutionToken ? { "X-Institution-Token": institutionToken } : {}),
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail?.detail !== undefined ? normalizeErrorDetail(detail.detail) : `HTTP ${res.status}`);
    }
    return (await res.json()) as T;
  };

  const check = async () => {
    setError(null);
    try {
      setReport(await post<ReadinessResponse>(clinicalPaths.readiness(caseId), { playbook_id: playbookId || undefined }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const requestConfirmation = async (itemIds: string[]) => {
    setError(null);
    try {
      const review = await post<CaseClinicalReview>(clinicalPaths.factConfirmation(caseId), {
        item_ids: itemIds,
        playbook_id: playbookId || undefined,
        share_with_reviewer_consent: shareConsent,
      });
      setFactReview(review);
      setDoctors(await clinicalRequest<ReviewerProfile[]>(`${clinicalPaths.reviewers()}?category=DOCTOR`));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const assignDoctor = async (doctorId: string) => {
    if (!factReview) return;
    setError(null);
    try {
      setFactReview(
        await clinicalRequest<CaseClinicalReview>(clinicalPaths.assign(caseId, factReview.review_id), {
          method: "POST",
          caseToken,
          body: { reviewer_id: doctorId },
        })
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const pendingFacts = report?.items.filter((i) => i.status === "NEEDS_CLINICAL_CONFIRMATION") ?? [];

  const counts = report
    ? report.items.reduce(
        (acc, i) => ({ ...acc, [TONE[i.status]]: acc[TONE[i.status]] + 1 }),
        { ok: 0, missing: 0, question: 0 } as Record<"ok" | "missing" | "question", number>
      )
    : null;

  return (
    <section aria-labelledby="readiness-title" className="case-panel bn-card readiness-panel">
      <h3 id="readiness-title">Pre-authorization readiness</h3>
      <p className="bn-fine">
        Checks which commonly requested documents can be found in your case. It does not predict approval.
      </p>
      <details className="ds-unlock">
        <summary>Hospital desk: apply your institution&apos;s private playbook</summary>
        <div className="grid-2">
          <input className="input-field" placeholder="Playbook ID (PB-…)" aria-label="Playbook ID" value={playbookId} onChange={(e) => setPlaybookId(e.target.value)} />
          <input
            className="input-field"
            type="password"
            placeholder="Institution credential"
            aria-label="Institution credential"
            value={institutionToken}
            onChange={(e) => setInstitutionToken(e.target.value)}
          />
        </div>
      </details>
      <div>
        <button type="button" className="btn btn-primary" onClick={check}>
          {report ? "Check again" : "Check documentation readiness"}
        </button>
      </div>
      {error && <StatePanel kind="error" onRetry={check}>{error}</StatePanel>}

      {report && counts && (
        <div className="readiness-result">
          <ListenSummary lang={lang} panel="readiness" summary={buildReadinessSummary(report.items, lang)} />
          <div className="readiness-meter" role="img" aria-label={`${counts.ok} found, ${counts.question} need a doctor, ${counts.missing} not found`}>
            {report.items.map((item) => (
              <span key={item.item_id} className={`readiness-cell is-${TONE[item.status]}`} title={item.label} />
            ))}
          </div>
          <div className="readiness-legend">
            <span><i className="readiness-dot is-ok" aria-hidden="true" /> {counts.ok} found</span>
            <span><i className="readiness-dot is-question" aria-hidden="true" /> {counts.question} need a doctor</span>
            <span><i className="readiness-dot is-missing" aria-hidden="true" /> {counts.missing} not found</span>
          </div>
          <div className="stat-label">Guidance used: {report.guidance_label}</div>
          <ul className="readiness-items">
            {report.items.map((item) => (
              <li key={item.item_id} className={`readiness-item is-${TONE[item.status]}`}>
                <span className="readiness-mark" aria-hidden="true">{MARK[item.status]}</span>
                <div className="readiness-text">
                  <strong>{item.label}</strong>
                  <span className="readiness-status">
                    {STATUS_TEXT[item.status]}
                    {item.evidence_strength === "KEYWORD_MATCH" && " (keyword found in document text — weak evidence)"}
                  </span>
                  {item.origin === "INSTITUTION_PLAYBOOK" && <span className="badge badge-info">playbook</span>}
                  {item.clinical_decision && item.clinical_decision.decision !== "PENDING" && (
                    <span className="readiness-status">
                      {humanizeEnum(item.clinical_decision.decision)} — {item.clinical_decision.reviewer_name} ({item.clinical_decision.reviewer_verification_label};
                      COI: {item.clinical_decision.coi_label})
                    </span>
                  )}
                  <ExplainTrail explanation={item.explanation} lang={lang} />
                </div>
              </li>
            ))}
          </ul>
          <div className="stat-label">Recommended action</div>
          <ul className="readiness-actions">
            {report.recommended_actions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
          <p className="bn-fine">{report.evidence_scope_note}</p>
          <p className="bn-fine">{report.disclaimer}</p>

          {pendingFacts.length > 0 && !factReview && (
            <div className="readiness-confirm">
              <label className="consent-wrapper">
                <input type="checkbox" className="consent-checkbox" checked={shareConsent} onChange={(e) => setShareConsent(e.target.checked)} />
                <span>I agree to share this case&apos;s de-identified evidence with the doctor I assign to confirm these facts.</span>
              </label>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={!shareConsent}
                onClick={() => requestConfirmation(pendingFacts.map((f) => f.item_id))}
              >
                Ask a doctor to confirm {pendingFacts.length} clinical fact(s)
              </button>
            </div>
          )}
          {factReview && (
            <div className="readiness-confirm">
              <p>Doctor confirmation request: {humanizeEnum(factReview.status)}</p>
              {factReview.assigned_reviewer ? (
                <ReviewerAttribution reviewer={factReview.assigned_reviewer} />
              ) : (
                <AssignReviewer directory={doctors} label="Assign doctor" onAssign={assignDoctor} />
              )}
              <p className="bn-fine">Re-run the readiness check after the doctor decides to see the result.</p>
            </div>
          )}
        </div>
      )}
    </section>
  );
};
