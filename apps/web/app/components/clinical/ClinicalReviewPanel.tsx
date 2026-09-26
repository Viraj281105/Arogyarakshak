"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  AuditEvent,
  CaseClinicalReview,
  ReviewerProfile,
  clinicalPaths,
  clinicalRequest,
} from "../../lib/clinical";
import { ClinicalStatementCard, ProvenanceBadge, ReviewerAttribution } from "./Attribution";

interface ClinicalReviewPanelProps {
  caseId: string;
  caseToken?: string;
  sourceModule: "billnyay" | "bimanyay" | "kadi";
  /** Why the system suggests human review (machine-derived), shown as context only. */
  recommendationReason?: string | null;
  suggestedQuestion?: string | null;
  trigger?: "MANUAL" | "PLAUSIBILITY_FLAG" | "DENIAL_CATEGORY" | "SAFETY_RULE";
  insurerName?: string;
}

const STATUS_TEXT: Record<CaseClinicalReview["status"], string> = {
  REQUESTED: "Requested — choose a reviewer",
  ASSIGNED: "Waiting for the reviewer to accept",
  IN_REVIEW: "Reviewer is working on it",
  COMPLETED: "Completed",
  DECLINED: "Reviewer declined — choose another",
  CANCELLED: "Cancelled — reviewer access revoked",
};

/**
 * Patient-side "Request Clinical Review". The patient decides what is shared and with whom;
 * the reviewer writes and confirms their own statement. Nothing here is written by AI.
 */
export const ClinicalReviewPanel: React.FC<ClinicalReviewPanelProps> = ({
  caseId,
  caseToken,
  sourceModule,
  recommendationReason,
  suggestedQuestion,
  trigger = "MANUAL",
  insurerName,
}) => {
  const [reviews, setReviews] = useState<CaseClinicalReview[]>([]);
  const [directory, setDirectory] = useState<ReviewerProfile[]>([]);
  const [question, setQuestion] = useState<string>(suggestedQuestion ?? "");
  const [shareConsent, setShareConsent] = useState(false);
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [audit, setAudit] = useState<Record<string, AuditEvent[]>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(
    () =>
      Promise.all([
        clinicalRequest<CaseClinicalReview[]>(clinicalPaths.caseReviews(caseId, sourceModule), { caseToken }),
        clinicalRequest<ReviewerProfile[]>(`${clinicalPaths.reviewers()}?category=DOCTOR`),
      ]),
    [caseId, caseToken, sourceModule]
  );

  useEffect(() => {
    let cancelled = false;
    fetchAll()
      .then(([list, doctors]) => {
        if (cancelled) return;
        setReviews(list);
        setDirectory(doctors);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [fetchAll]);

  const load = async () => {
    const [list, doctors] = await fetchAll();
    setReviews(list);
    setDirectory(doctors);
  };

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const requestReview = () =>
    run(() =>
      clinicalRequest(clinicalPaths.caseReviews(caseId), {
        method: "POST",
        caseToken,
        body: {
          source_module: sourceModule,
          clinical_question: question.trim() || undefined,
          trigger,
          insurer_name: insurerName || undefined,
          share_with_reviewer_consent: shareConsent,
        },
      })
    );

  const assignReviewer = (reviewId: string) =>
    run(() =>
      clinicalRequest(clinicalPaths.assign(caseId, reviewId), {
        method: "POST",
        caseToken,
        body: { reviewer_id: selected[reviewId] },
      })
    );

  const cancelReview = (reviewId: string) =>
    run(() => clinicalRequest(clinicalPaths.cancel(caseId, reviewId), { method: "POST", caseToken }));

  const toggleAudit = async (reviewId: string) => {
    if (audit[reviewId]) {
      setAudit((prev) => {
        const next = { ...prev };
        delete next[reviewId];
        return next;
      });
      return;
    }
    try {
      const events = await clinicalRequest<AuditEvent[]>(clinicalPaths.caseAudit(caseId, reviewId), { caseToken });
      setAudit((prev) => ({ ...prev, [reviewId]: events }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const openReviews = reviews.filter((r) => r.review_type === "CLINICAL_STATEMENT");

  return (
    <section
      aria-labelledby={`clinical-review-${sourceModule}`}
      style={{
        border: "1px solid var(--border-medium)",
        borderRadius: "var(--radius-md)",
        padding: "1.25rem",
        marginBottom: "1.5rem",
        background: "var(--bg-surface-elevated)",
      }}
    >
      <h3 id={`clinical-review-${sourceModule}`}>🩺 Clinical Review by a Named Doctor</h3>
      <p style={{ fontSize: "0.85rem", marginBottom: "0.75rem" }}>
        Some findings need a clinician&apos;s judgment, which ArogyaRakshak will not invent. You can share selected case
        evidence with a doctor you choose; they write and sign their own statement, with their conflict of interest
        disclosed.
      </p>
      {recommendationReason && (
        <div style={{ fontSize: "0.85rem", marginBottom: "0.75rem" }}>
          <ProvenanceBadge provenance="AI_DERIVED" /> Why review is suggested: {recommendationReason}
        </div>
      )}

      {error && (
        <div role="alert" style={{ color: "#fca5a5", fontSize: "0.85rem", marginBottom: "0.75rem" }}>
          ⚠️ {error}
        </div>
      )}

      <label className="input-label" htmlFor={`cq-${sourceModule}`}>
        Question for the reviewer (optional — a neutral default is used otherwise)
      </label>
      <textarea
        id={`cq-${sourceModule}`}
        className="textarea-field"
        rows={3}
        maxLength={1000}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
      />
      <label className="consent-wrapper" style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start", margin: "0.75rem 0" }}>
        <input type="checkbox" checked={shareConsent} onChange={(e) => setShareConsent(e.target.checked)} />
        <span style={{ fontSize: "0.85rem" }}>
          I agree to share this case&apos;s extracted, de-identified evidence with the reviewer I assign, for this review
          only. I can cancel at any time to revoke their access.
        </span>
      </label>
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        <button type="button" className="btn btn-primary" disabled={busy || !shareConsent} onClick={requestReview}>
          Request Clinical Review
        </button>
        {openReviews.length > 0 && (
          <button type="button" className="btn" style={{ border: "1px solid var(--border-subtle)" }} disabled={busy} onClick={() => run(async () => undefined)}>
            ↻ Refresh status
          </button>
        )}
      </div>

      {openReviews.map((review) => (
        <div
          key={review.review_id}
          style={{ borderTop: "1px solid var(--border-subtle)", marginTop: "1.25rem", paddingTop: "1rem" }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "0.5rem" }}>
            <strong>Review {review.review_id}</strong>
            <span className={`badge ${review.status === "COMPLETED" ? "badge-success" : "badge-info"}`}>
              {STATUS_TEXT[review.status]}
            </span>
          </div>
          <p style={{ fontSize: "0.8rem", margin: "0.35rem 0" }}>
            Shared with the reviewer:{" "}
            {review.evidence_shared.map((e) => `${e.label} (${e.provenance})`).join(", ")}
          </p>

          {review.assigned_reviewer && (
            <ReviewerAttribution reviewer={review.assigned_reviewer} coiLabel={review.coi_label} coiDisclosure={review.coi_disclosure} />
          )}

          {(review.status === "REQUESTED" || review.status === "DECLINED" || review.status === "ASSIGNED") && (
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "0.5rem" }}>
              <select
                className="select-field"
                aria-label="Choose a reviewer"
                value={selected[review.review_id] ?? ""}
                onChange={(e) => setSelected((prev) => ({ ...prev, [review.review_id]: e.target.value }))}
              >
                <option value="">Choose a doctor…</option>
                {directory.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} — {d.specialty ?? d.category_label} — {d.verification_label}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={busy || !selected[review.review_id]}
                onClick={() => assignReviewer(review.review_id)}
              >
                Assign reviewer
              </button>
            </div>
          )}

          {review.draft_in_progress && !review.current_statement && (
            <p style={{ fontSize: "0.85rem", marginTop: "0.5rem" }}>
              The reviewer is drafting. Nothing is shown until they finalize and confirm it themselves.
            </p>
          )}
          {review.current_statement ? (
            <div style={{ marginTop: "0.75rem" }}>
              <ClinicalStatementCard statement={review.current_statement} />
            </div>
          ) : (
            review.status !== "CANCELLED" && (
              <p style={{ fontSize: "0.85rem", marginTop: "0.5rem" }}>
                No human clinical statement exists for this review yet.
              </p>
            )
          )}
          {review.statement_history.length > 1 && (
            <details style={{ marginTop: "0.5rem" }}>
              <summary>Version history ({review.statement_history.length})</summary>
              {review.statement_history.map((s) => (
                <ClinicalStatementCard key={s.statement_id} statement={s} />
              ))}
            </details>
          )}

          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "0.75rem" }}>
            <button type="button" className="btn" style={{ border: "1px solid var(--border-subtle)" }} onClick={() => toggleAudit(review.review_id)}>
              {audit[review.review_id] ? "Hide audit trail" : "Show audit trail"}
            </button>
            {review.status !== "CANCELLED" && (
              <button
                type="button"
                className="btn"
                style={{ border: "1px solid var(--status-danger)", color: "var(--status-danger)" }}
                disabled={busy}
                onClick={() => cancelReview(review.review_id)}
              >
                Cancel &amp; revoke access
              </button>
            )}
          </div>
          {audit[review.review_id] && (
            <ol className="timeline-list" style={{ marginTop: "0.5rem", fontSize: "0.8rem" }}>
              {audit[review.review_id].map((e) => (
                <li key={e.id} className="timeline-item">
                  {e.created_at} — {e.event_type} ({e.actor_type}
                  {e.actor_id ? ` ${e.actor_id}` : ""})
                </li>
              ))}
            </ol>
          )}
        </div>
      ))}
    </section>
  );
};
