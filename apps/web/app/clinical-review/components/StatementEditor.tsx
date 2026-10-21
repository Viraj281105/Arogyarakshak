"use client";

import React from "react";
import { ClinicalStatement, EvidenceItem } from "../../lib/clinical";
import { ClinicalStatementCard } from "../../components/clinical/Attribution";
import { StatePanel } from "../../components/clinical/StatePanel";
import { TONE_CLASS, humanizeEnum } from "../../lib/labels";
import { ReviewerDetail, StatementEditorState } from "../types";

type StatementAction = "submit" | "revise" | "return-to-draft";

/** The reviewer's own statement: draft, lock, finalize (with the server's confirmation
 *  sentence ticked by the reviewer). ArogyaRakshak never writes any of this text. */
export function StatementEditor({
  detail,
  evidence,
  currentDraft,
  editor,
  setEditor,
  confirmTicked,
  setConfirmTicked,
  onSaveDraft,
  onStatementAction,
  onFinalize,
}: {
  detail: ReviewerDetail;
  evidence: EvidenceItem[] | null;
  currentDraft: ClinicalStatement | undefined;
  editor: StatementEditorState;
  setEditor: (value: StatementEditorState) => void;
  confirmTicked: boolean;
  setConfirmTicked: (value: boolean) => void;
  onSaveDraft: () => void;
  onStatementAction: (statementId: string, action: StatementAction) => void;
  onFinalize: (statementId: string) => void;
}) {
  return (
    <div style={{ marginTop: "1rem" }}>
      <h4>
        Your statement{" "}
        <span className={TONE_CLASS["human-authored"]}>✍ Written by you</span>{" "}
        {currentDraft ? `Version ${currentDraft.statement_version} — ${humanizeEnum(currentDraft.status)}` : "(new draft)"}
      </h4>
      <p style={{ fontSize: "0.75rem", opacity: 0.85 }}>
        ArogyaRakshak never drafts, edits or completes this text. It is shown to the patient and attached to their
        documents verbatim, with your name, verification status and conflict-of-interest declaration.
      </p>
      <label className="input-label" htmlFor="stmt-text">
        Your professional statement, in your own words
      </label>
      <textarea
        id="stmt-text"
        className="textarea-field"
        rows={6}
        maxLength={8000}
        value={editor.text}
        disabled={currentDraft?.status === "UNDER_REVIEW"}
        onChange={(e) => setEditor({ ...editor, text: e.target.value })}
      />
      <label className="input-label" htmlFor="stmt-limits">
        Limitations of your review (required)
      </label>
      <textarea
        id="stmt-limits"
        className="textarea-field"
        rows={3}
        maxLength={3000}
        value={editor.limitations}
        disabled={currentDraft?.status === "UNDER_REVIEW"}
        onChange={(e) => setEditor({ ...editor, limitations: e.target.value })}
      />
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "0.5rem" }}>
        {currentDraft?.status !== "UNDER_REVIEW" && (
          <button type="button" className="btn btn-secondary" disabled={!evidence} onClick={onSaveDraft}>
            Save draft
          </button>
        )}
        {currentDraft?.status === "DRAFT" && (
          <button type="button" className="btn" style={{ border: "1px solid var(--border-subtle)" }} onClick={() => onStatementAction(currentDraft.statement_id, "submit")}>
            Lock for finalization
          </button>
        )}
        {currentDraft?.status === "UNDER_REVIEW" && (
          <button type="button" className="btn" style={{ border: "1px solid var(--border-subtle)" }} onClick={() => onStatementAction(currentDraft.statement_id, "return-to-draft")}>
            Back to editing
          </button>
        )}
      </div>
      {currentDraft && (
        <div style={{ marginTop: "1rem", padding: "0.75rem", border: "1px solid var(--status-warning)", borderRadius: "var(--radius-md)" }}>
          <div className="stat-label">Before you can finalize</div>
          <ul style={{ listStyle: "none", paddingLeft: 0, fontSize: "0.85rem", margin: "0.25rem 0 0.75rem" }}>
            {[
              ["Conflict of interest declared", !!detail.coi_label],
              ["Evidence you reviewed is selected (saved in the draft)", currentDraft.evidence_reviewed.length > 0],
              ["Statement written in your own words", currentDraft.reviewer_statement.trim().length > 0],
              ["Limitations of your review stated", currentDraft.limitations.trim().length > 0],
              ["You tick the confirmation below yourself", confirmTicked],
            ].map(([label, done]) => (
              <li key={String(label)}>
                {done ? "✓" : "○"} {label}
              </li>
            ))}
          </ul>
          <p style={{ fontSize: "0.75rem", opacity: 0.85 }}>
            Finalizing freezes this version (a content hash is recorded). Later changes create a new version; the
            patient then sees only the newest finalized one.
          </p>
          <label style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start" }}>
            <input type="checkbox" checked={confirmTicked} onChange={(e) => setConfirmTicked(e.target.checked)} />
            <span>{detail.finalization_confirmation_text}</span>
          </label>
          <button
            type="button"
            className="btn btn-primary"
            style={{ marginTop: "0.5rem" }}
            disabled={!confirmTicked}
            onClick={() => onFinalize(currentDraft.statement_id)}
          >
            Finalize and sign
          </button>
        </div>
      )}
    </div>
  );
}

/** Finalized, superseded and withdrawn versions, with revise / withdraw on the current one. */
export function PublishedStatements({
  detail,
  finalized,
  currentDraft,
  withdrawReason,
  setWithdrawReason,
  onStatementAction,
  onWithdraw,
}: {
  detail: ReviewerDetail;
  finalized: ClinicalStatement | undefined;
  currentDraft: ClinicalStatement | undefined;
  withdrawReason: string;
  setWithdrawReason: (value: string) => void;
  onStatementAction: (statementId: string, action: StatementAction) => void;
  onWithdraw: (statementId: string) => void;
}) {
  const published = detail.statements.filter((s) => s.status !== "DRAFT" && s.status !== "UNDER_REVIEW");
  if (published.length === 0) return null;
  return (
    <div style={{ marginTop: "1rem" }}>
      <h4>Your published versions</h4>
      {finalized && !currentDraft && (
        <StatePanel kind="info">
          Version {finalized.statement_version} is finalized and immutable. To change it, create a new version;
          to retract it, withdraw it with a reason — a withdrawn statement is removed from the patient&apos;s current
          documents.
        </StatePanel>
      )}
      {published.map((s) => (
        <div key={s.statement_id}>
          <ClinicalStatementCard statement={s} />
          {s.status === "FINALIZED" && !currentDraft && (
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
              <button type="button" className="btn btn-secondary" onClick={() => onStatementAction(s.statement_id, "revise")}>
                Create new version
              </button>
              <input
                className="input-field"
                style={{ maxWidth: 320 }}
                placeholder="Reason for withdrawal"
                value={withdrawReason}
                onChange={(e) => setWithdrawReason(e.target.value)}
              />
              <button
                type="button"
                className="btn"
                style={{ border: "1px solid var(--status-danger)", color: "var(--status-danger)" }}
                disabled={!withdrawReason.trim()}
                onClick={() => onWithdraw(s.statement_id)}
              >
                Withdraw
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
