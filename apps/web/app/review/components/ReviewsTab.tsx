"use client";

import React, { useState } from "react";
import { AuditEvent, ClinicalStatement, EvidenceItem, FactDecision, clinicalPaths } from "../../lib/clinical";
import { StatePanel } from "../../components/clinical/StatePanel";
import { TONE_CLASS, formatTimestamp, humanizeEnum } from "../../lib/labels";
import { AssignedReview, FactInput, Guard, MODULE_LABEL, ReviewerCall, ReviewerDetail, StatementEditorState } from "../types";
import { EvidencePanel } from "./EvidencePanel";
import { FactConfirmations } from "./FactConfirmations";
import { ReviewSummary } from "./ReviewSummary";
import { PublishedStatements, StatementEditor } from "./StatementEditor";

const EMPTY_EDITOR: StatementEditorState = { statementId: "", selected: [], text: "", limitations: "" };

/** The reviewer's queue and the open review: accept with a COI declaration, read the
 *  shared evidence, write/finalize a statement or decide facts, read the audit trail. */
export function ReviewsTab({
  guard,
  call,
  queue,
  setQueue,
  refreshQueue,
}: {
  guard: Guard;
  call: ReviewerCall;
  queue: AssignedReview[];
  setQueue: (q: AssignedReview[]) => void;
  refreshQueue: () => Promise<void>;
}) {
  const [detail, setDetail] = useState<ReviewerDetail | null>(null);
  const [evidence, setEvidence] = useState<EvidenceItem[] | null>(null);
  const [audit, setAudit] = useState<AuditEvent[] | null>(null);
  const [coi, setCoi] = useState({ category: "", disclosure: "" });
  const [editor, setEditor] = useState<StatementEditorState>(EMPTY_EDITOR);
  const [confirmTicked, setConfirmTicked] = useState(false);
  const [withdrawReason, setWithdrawReason] = useState("");
  const [factInput, setFactInput] = useState<FactInput>({});

  const openReview = (reviewId: string) =>
    guard(async () => {
      const d = await call<ReviewerDetail>(clinicalPaths.reviewerReview(reviewId));
      setDetail(d);
      setEvidence(null);
      setAudit(null);
      setConfirmTicked(false);
      const draft = d.statements.find((s: ClinicalStatement) => s.status === "DRAFT" || s.status === "UNDER_REVIEW");
      setEditor(
        draft
          ? { statementId: draft.statement_id, selected: draft.evidence_reviewed.map((e) => e.item_id), text: draft.reviewer_statement, limitations: draft.limitations }
          : EMPTY_EDITOR
      );
    });

  const accept = () =>
    guard(async () => {
      await call(clinicalPaths.accept(detail!.review_id), "POST", { coi_category: coi.category, coi_disclosure: coi.disclosure || null });
      await openReview(detail!.review_id);
      setQueue(await call<AssignedReview[]>(clinicalPaths.assigned()));
    }, "Accepted. Your conflict-of-interest declaration is recorded.");

  const decline = () =>
    guard(async () => {
      await call(clinicalPaths.decline(detail!.review_id), "POST", { reason: null });
      setDetail(null);
      await refreshQueue();
    }, "Declined.");

  const loadEvidence = () =>
    guard(async () => setEvidence((await call<{ evidence: EvidenceItem[] }>(clinicalPaths.evidence(detail!.review_id))).evidence));

  const saveDraft = () =>
    guard(async () => {
      const body = { evidence_reviewed: editor.selected, reviewer_statement: editor.text, limitations: editor.limitations };
      const saved = editor.statementId
        ? await call<ClinicalStatement>(clinicalPaths.statement(detail!.review_id, editor.statementId), "PUT", body)
        : await call<ClinicalStatement>(clinicalPaths.statements(detail!.review_id), "POST", body);
      setEditor((prev) => ({ ...prev, statementId: saved.statement_id }));
      await openReview(detail!.review_id);
    }, "Draft saved. Only you can see drafts.");

  const statementAction = (statementId: string, action: "submit" | "revise" | "return-to-draft") =>
    guard(async () => {
      await call(`${clinicalPaths.statement(detail!.review_id, statementId)}/${action}`, "POST");
      await openReview(detail!.review_id);
    });

  const finalizeStatement = (statementId: string) =>
    guard(async () => {
      // The reviewer ticks the box themselves; the sentence is the server's, shown above.
      await call(`${clinicalPaths.statement(detail!.review_id, statementId)}/finalize`, "POST", {
        confirmation: confirmTicked,
        confirmation_text: confirmTicked ? detail!.finalization_confirmation_text : "",
      });
      await openReview(detail!.review_id);
    }, "Statement finalized. It is now immutable; changes create a new version.");

  const withdraw = (statementId: string) =>
    guard(async () => {
      await call(`${clinicalPaths.statement(detail!.review_id, statementId)}/withdraw`, "POST", { reason: withdrawReason });
      await openReview(detail!.review_id);
    }, "Statement withdrawn.");

  const decideFact = (fact: FactDecision) =>
    guard(async () => {
      const input = factInput[fact.fact_id];
      await call(clinicalPaths.factDecision(detail!.review_id, fact.fact_id), "POST", {
        decision: input?.decision,
        note: input?.note || null,
        confirmation: !!input?.confirm,
        confirmation_text: input?.confirm ? detail!.fact_decision_confirmation_text : "",
      });
      await openReview(detail!.review_id);
    }, "Decision recorded.");

  const showAudit = () => guard(async () => setAudit(await call<AuditEvent[]>(clinicalPaths.reviewerAudit(detail!.review_id))));

  const currentDraft = detail?.statements.find((s) => s.status === "DRAFT" || s.status === "UNDER_REVIEW");
  const finalized = detail?.statements.find((s) => s.status === "FINALIZED");
  const canWork = detail && (detail.status === "IN_REVIEW" || detail.status === "COMPLETED");

  return (
    <div className="rv-split">
      <section className="case-panel bn-card rv-queue" aria-labelledby="rv-queue-title">
        <div className="case-panel-head">
          <h3 id="rv-queue-title">Assigned to you</h3>
          <button type="button" className="btn btn-ghost btn-compact" onClick={refreshQueue}>
            Refresh
          </button>
        </div>
        {queue.length === 0 && (
          <StatePanel kind="empty">
            No reviews are assigned to you yet. A patient assigns you by the reviewer ID shown above; press refresh after they do.
          </StatePanel>
        )}
        <ul className="rv-queue-list">
          {queue.map((r) => (
            <li key={r.review_id}>
              <button
                type="button"
                className={`rv-queue-item ${detail?.review_id === r.review_id ? "is-open" : ""}`}
                aria-current={detail?.review_id === r.review_id ? "true" : undefined}
                onClick={() => openReview(r.review_id)}
              >
                <strong>{r.review_type === "FACT_CONFIRMATION" ? "Confirm clinical facts" : "Clinical statement"}</strong>
                <span className="rv-queue-module">{MODULE_LABEL[r.source_module] ?? humanizeEnum(r.source_module)}</span>
                <span className="rv-queue-meta">
                  <span className={TONE_CLASS.neutral}>{humanizeEnum(r.status)}</span>
                  {r.created_at && <span>requested {formatTimestamp(r.created_at)}</span>}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      {!detail && queue.length > 0 && (
        <div className="module-empty rv-placeholder">
          <div>
            <strong>Choose a review to open it</strong>
            <p>Its question, the evidence the patient shared with you and your statement appear here.</p>
          </div>
        </div>
      )}

      {detail && (
        <section className="case-panel bn-card rv-detail" aria-labelledby="review-detail">
          <ReviewSummary detail={detail} coi={coi} setCoi={setCoi} onAccept={accept} onDecline={decline} />

          {canWork && (
            <>
              <button type="button" className="btn btn-secondary" onClick={loadEvidence}>
                {evidence ? "Reload shared evidence" : "Open shared evidence"}
              </button>
              {evidence && (
                <EvidencePanel
                  detail={detail}
                  evidence={evidence}
                  editor={editor}
                  setEditor={setEditor}
                  selectionLocked={!!finalized && !currentDraft}
                />
              )}

              {detail.review_type === "CLINICAL_STATEMENT" && (!finalized || currentDraft) && (
                <StatementEditor
                  detail={detail}
                  evidence={evidence}
                  currentDraft={currentDraft}
                  editor={editor}
                  setEditor={setEditor}
                  confirmTicked={confirmTicked}
                  setConfirmTicked={setConfirmTicked}
                  onSaveDraft={saveDraft}
                  onStatementAction={statementAction}
                  onFinalize={finalizeStatement}
                />
              )}

              {detail.review_type === "CLINICAL_STATEMENT" && (
                <PublishedStatements
                  detail={detail}
                  finalized={finalized}
                  currentDraft={currentDraft}
                  withdrawReason={withdrawReason}
                  setWithdrawReason={setWithdrawReason}
                  onStatementAction={statementAction}
                  onWithdraw={withdraw}
                />
              )}

              {detail.review_type === "FACT_CONFIRMATION" && (
                <FactConfirmations detail={detail} factInput={factInput} setFactInput={setFactInput} onDecide={decideFact} />
              )}
            </>
          )}

          <div>
            <button type="button" className="btn btn-ghost btn-compact" onClick={showAudit}>
              {audit ? "Refresh audit trail" : "Show audit trail"}
            </button>
          </div>
          {audit && (
            <ol className="timeline rv-audit">
              {audit.map((e) => (
                <li key={e.id} className="timeline-event">
                  <span className="timeline-dot" aria-hidden="true" />
                  <div className="timeline-meta">
                    <time dateTime={e.created_at}>{formatTimestamp(e.created_at)}</time>
                    <span>{humanizeEnum(e.actor_type)}</span>
                  </div>
                  <strong className="timeline-label">{humanizeEnum(e.event_type)}</strong>
                </li>
              ))}
            </ol>
          )}
        </section>
      )}
    </div>
  );
}
