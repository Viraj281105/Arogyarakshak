"use client";

import React, { useState } from "react";
import { API_BASE, caseAuthHeaders, normalizeErrorDetail } from "../../hooks/useApi";
import { ReviewerProfile, CaseClinicalReview, clinicalPaths, clinicalRequest } from "../../lib/clinical";
import { ReviewerAttribution } from "./Attribution";

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
}

interface ReadinessResponse {
  case_id: string;
  guidance_label: string;
  items: ReadinessItem[];
  recommended_actions: string[];
  ready_to_submit: boolean;
  disclaimer: string;
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

const STATUS_TEXT: Record<ReadinessItem["status"], string> = {
  PRESENT: "found in your documents",
  MISSING: "not found in the supplied documents",
  NEEDS_CLINICAL_CONFIRMATION: "clinical fact — needs a doctor's confirmation",
  CONFIRMED_BY_REVIEWER: "confirmed by a named reviewer",
  REJECTED_BY_REVIEWER: "a reviewer did NOT confirm this",
  REVIEWER_COULD_NOT_DETERMINE: "reviewer could not determine this from the records",
};

/**
 * DaaviSetu preauth readiness: documentation completeness only. It never predicts approval
 * and never marks a clinical fact satisfied without a named reviewer's decision.
 */
export const PreauthReadinessPanel: React.FC<{ caseId: string; caseToken?: string }> = ({ caseId, caseToken }) => {
  const [report, setReport] = useState<ReadinessResponse | null>(null);
  const [playbookId, setPlaybookId] = useState("");
  const [institutionToken, setInstitutionToken] = useState("");
  const [shareConsent, setShareConsent] = useState(false);
  const [factReview, setFactReview] = useState<CaseClinicalReview | null>(null);
  const [doctors, setDoctors] = useState<ReviewerProfile[]>([]);
  const [doctorId, setDoctorId] = useState("");
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

  const assignDoctor = async () => {
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

  return (
    <section
      aria-labelledby="readiness-title"
      style={{ border: "1px solid var(--border-medium)", borderRadius: "var(--radius-md)", padding: "1.25rem", marginBottom: "1.5rem" }}
    >
      <h3 id="readiness-title">📑 Pre-authorization readiness</h3>
      <p style={{ fontSize: "0.85rem", marginBottom: "0.75rem" }}>
        Checks which commonly requested documents can be found in your case. It does not predict approval.
      </p>
      <details style={{ marginBottom: "0.75rem" }}>
        <summary style={{ fontSize: "0.85rem" }}>Hospital desk: apply your institution&apos;s private playbook</summary>
        <div className="grid-2" style={{ marginTop: "0.5rem" }}>
          <input className="input-field" placeholder="Playbook ID (PB-…)" value={playbookId} onChange={(e) => setPlaybookId(e.target.value)} />
          <input
            className="input-field"
            type="password"
            placeholder="Institution credential"
            value={institutionToken}
            onChange={(e) => setInstitutionToken(e.target.value)}
          />
        </div>
      </details>
      <button type="button" className="btn btn-primary" onClick={check}>
        Check documentation readiness
      </button>
      {error && (
        <div role="alert" style={{ color: "#fca5a5", fontSize: "0.85rem", marginTop: "0.75rem" }}>
          ⚠️ {error}
        </div>
      )}

      {report && (
        <div style={{ marginTop: "1rem" }}>
          <div className="stat-label">Guidance used: {report.guidance_label}</div>
          <ul style={{ listStyle: "none", padding: 0, margin: "0.5rem 0" }}>
            {report.items.map((item) => (
              <li key={item.item_id} style={{ padding: "0.4rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
                <strong>
                  {MARK[item.status]} {item.label}
                </strong>{" "}
                <span style={{ fontSize: "0.8rem" }}>— {STATUS_TEXT[item.status]}</span>
                {item.evidence_strength === "KEYWORD_MATCH" && (
                  <span style={{ fontSize: "0.75rem", opacity: 0.8 }}> (keyword found in document text — weak evidence)</span>
                )}
                {item.origin === "INSTITUTION_PLAYBOOK" && <span className="badge badge-info" style={{ marginLeft: "0.4rem" }}>playbook</span>}
                {item.clinical_decision && item.clinical_decision.decision !== "PENDING" && (
                  <div style={{ fontSize: "0.75rem" }}>
                    {item.clinical_decision.decision} by {item.clinical_decision.reviewer_name} ({item.clinical_decision.reviewer_verification_label};
                    COI: {item.clinical_decision.coi_label})
                  </div>
                )}
              </li>
            ))}
          </ul>
          <div className="stat-label">Recommended action</div>
          <ul style={{ fontSize: "0.85rem", paddingLeft: "1.1rem" }}>
            {report.recommended_actions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
          <p style={{ fontSize: "0.75rem", opacity: 0.8 }}>{report.disclaimer}</p>

          {pendingFacts.length > 0 && !factReview && (
            <div style={{ marginTop: "0.75rem" }}>
              <label className="consent-wrapper" style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start" }}>
                <input type="checkbox" checked={shareConsent} onChange={(e) => setShareConsent(e.target.checked)} />
                <span style={{ fontSize: "0.85rem" }}>I agree to share this case&apos;s de-identified evidence with the doctor I assign to confirm these facts.</span>
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
            <div style={{ marginTop: "0.75rem", fontSize: "0.85rem" }}>
              <p>
                Confirmation request {factReview.review_id}: {factReview.status}
              </p>
              {factReview.assigned_reviewer ? (
                <ReviewerAttribution reviewer={factReview.assigned_reviewer} />
              ) : (
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  <select className="select-field" aria-label="Choose a doctor" value={doctorId} onChange={(e) => setDoctorId(e.target.value)}>
                    <option value="">Choose a doctor…</option>
                    {doctors.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} — {d.verification_label}
                      </option>
                    ))}
                  </select>
                  <button type="button" className="btn btn-secondary" disabled={!doctorId} onClick={assignDoctor}>
                    Assign doctor
                  </button>
                </div>
              )}
              <p style={{ fontSize: "0.75rem", opacity: 0.8 }}>Re-run the readiness check after the doctor decides to see the result.</p>
            </div>
          )}
        </div>
      )}
    </section>
  );
};
