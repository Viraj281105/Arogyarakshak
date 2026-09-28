"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  AuditEvent,
  CaseClinicalReview,
  PROVENANCE_LABELS,
  ReviewerProfile,
  clinicalPaths,
  clinicalRequest,
} from "../../lib/clinical";
import { AssignReviewer } from "./AssignReviewer";
import { ClinicalStatementCard, ProvenanceBadge, ReviewerAttribution } from "./Attribution";
import { StatePanel } from "./StatePanel";
import { TONE_CLASS, formatTimestamp, humanizeEnum } from "../../lib/labels";

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
  REQUESTED: "Review requested — choose a reviewer",
  ASSIGNED: "Reviewer assigned — waiting for them to accept",
  IN_REVIEW: "Under clinical review",
  COMPLETED: "Statement finalized",
  DECLINED: "Reviewer declined — choose another",
  CANCELLED: "Cancelled — reviewer access revoked",
};

/** "9 billing items (machine-derived), 1 diagnosis (machine-derived), …" instead of a long list. */
function summarizeEvidence(items: CaseClinicalReview["evidence_shared"]): string {
  const counts = new Map<string, number>();
  for (const e of items) {
    const prov = (PROVENANCE_LABELS[e.provenance] ?? humanizeEnum(e.provenance)).toLowerCase();
    const key = e.label.toLowerCase().includes(prov) ? e.label : `${e.label} (${prov})`;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return [...counts.entries()].map(([k, n]) => (n > 1 ? `${n} × ${k}` : k)).join(", ");
}

/** Where a review is, as four patient-readable steps. */
function reviewSteps(review: CaseClinicalReview): { label: string; done: boolean }[] {
  const accepted = review.status === "IN_REVIEW" || review.status === "COMPLETED";
  return [
    { label: "Review requested (you consented to share)", done: true },
    { label: "Reviewer assigned", done: !!review.assigned_reviewer && review.status !== "REQUESTED" && review.status !== "DECLINED" },
    { label: "Reviewer accepted and declared any conflict of interest", done: accepted },
    { label: "Doctor-authored statement finalized", done: !!review.current_statement },
  ];
}

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
  const [audit, setAudit] = useState<Record<string, AuditEvent[]>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [initialLoad, setInitialLoad] = useState(true);

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
      })
      .finally(() => {
        if (!cancelled) setInitialLoad(false);
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

  const assignReviewer = (reviewId: string, reviewerId: string) =>
    run(() =>
      clinicalRequest(clinicalPaths.assign(caseId, reviewId), {
        method: "POST",
        caseToken,
        body: { reviewer_id: reviewerId },
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

      {initialLoad && <StatePanel kind="loading">Loading clinical reviews for this case…</StatePanel>}
      {error && (
        <StatePanel kind="error" onRetry={() => run(async () => undefined)}>
          {error}
        </StatePanel>
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
            <strong>Clinical review requested {formatTimestamp(review.created_at)}</strong>
            <span className={review.status === "COMPLETED" ? TONE_CLASS.success : review.status === "CANCELLED" ? TONE_CLASS.warning : TONE_CLASS.neutral}>
              {STATUS_TEXT[review.status]}
            </span>
          </div>
          {review.status !== "CANCELLED" && (
            <ol aria-label="Review progress" style={{ listStyle: "none", paddingLeft: 0, margin: "0.5rem 0", fontSize: "0.82rem" }}>
              {reviewSteps(review).map((step) => (
                <li key={step.label} style={{ opacity: step.done ? 1 : 0.6 }}>
                  {step.done ? "✓" : "○"} {step.label}
                </li>
              ))}
            </ol>
          )}
          <p style={{ fontSize: "0.8rem", margin: "0.35rem 0" }}>
            Shared with the reviewer:{" "}
            {review.evidence_shared.length === 0
              ? "nothing yet"
              : summarizeEvidence(review.evidence_shared)}
          </p>

          {review.assigned_reviewer && (
            <ReviewerAttribution reviewer={review.assigned_reviewer} coiLabel={review.coi_label} coiDisclosure={review.coi_disclosure} />
          )}

          {(review.status === "REQUESTED" || review.status === "DECLINED" || review.status === "ASSIGNED") && (
            <AssignReviewer
              directory={directory}
              disabled={busy}
              label="Assign doctor"
              onAssign={(reviewerId) => assignReviewer(review.review_id, reviewerId)}
            />
          )}

          {review.draft_in_progress && !review.current_statement && (
            <p style={{ fontSize: "0.85rem", marginTop: "0.5rem" }}>
              The reviewer is drafting. Nothing is shown until they finalize and confirm it themselves.
            </p>
          )}
          {review.current_statement ? (
            <div style={{ marginTop: "0.75rem" }}>
              <StatePanel kind="success">
                A named doctor finalized their own statement. It is shown verbatim below and attached to your appeal
                documents with their conflict-of-interest declaration.
              </StatePanel>
              <ClinicalStatementCard statement={review.current_statement} />
            </div>
          ) : review.statement_history.some((s) => s.status === "WITHDRAWN") ? (
            <StatePanel kind="warning">
              The reviewer withdrew their statement. It is no longer attached to your documents — download the appeal PDF again.
            </StatePanel>
          ) : (
            review.status !== "CANCELLED" && (
              <p style={{ fontSize: "0.85rem", marginTop: "0.5rem" }}>
                No doctor-authored statement exists for this review yet. ArogyaRakshak does not write one for them.
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
                  {formatTimestamp(e.created_at)} — {humanizeEnum(e.event_type)} ({humanizeEnum(e.actor_type)})
                </li>
              ))}
            </ol>
          )}
        </div>
      ))}
    </section>
  );
};
