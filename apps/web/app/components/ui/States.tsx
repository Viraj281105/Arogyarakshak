import React from "react";
import CircleAlert from "lucide-react/icons/circle-alert";
import FileQuestion from "lucide-react/icons/file-question-mark";
import Inbox from "lucide-react/icons/inbox";
import PuzzleIcon from "lucide-react/icons/puzzle";

/**
 * The five page/panel states every Wave 3 screen must have (plan section 4). Server-safe. Each
 * state says what happened in words; icons are decorative. Actions are passed in as nodes so the
 * caller decides whether a retry exists (an error offers one only when the caller can retry).
 */

export function LoadingState({ label = "Loading…", minHeight = "8rem" }: { label?: string; minHeight?: string }) {
  return (
    <div className="ui-state ui-state-loading" role="status" aria-live="polite" aria-busy="true" style={{ minHeight }}>
      <span className="spinner" aria-hidden="true" />
      <p>{label}</p>
    </div>
  );
}

export function EmptyState({ title, children, action }: { title: string; children?: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="ui-state ui-state-empty" role="status">
      <Inbox size={22} aria-hidden="true" />
      <div>
        <p className="ui-state-title">{title}</p>
        {children && <div className="ui-state-body">{children}</div>}
        {action && <div className="ui-state-actions">{action}</div>}
      </div>
    </div>
  );
}

export function ErrorState({ title = "Something went wrong", children, action }: { title?: string; children?: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="ui-state ui-state-error" role="alert">
      <CircleAlert size={22} aria-hidden="true" />
      <div>
        <p className="ui-state-title">{title}</p>
        {children && <div className="ui-state-body">{children}</div>}
        {action && <div className="ui-state-actions">{action}</div>}
      </div>
    </div>
  );
}

/** Some parts of a result are present and some are not; lists what is missing so it is not mistaken for complete. */
export function PartialResultState({
  title = "Partial result",
  missing,
  children,
}: {
  title?: string;
  /** What could not be produced, in plain words. Required: a partial state must say what is partial. */
  missing: readonly string[];
  children?: React.ReactNode;
}) {
  return (
    <div className="ui-state ui-state-partial" role="status">
      <PuzzleIcon size={22} aria-hidden="true" />
      <div>
        <p className="ui-state-title">{title}</p>
        {children && <div className="ui-state-body">{children}</div>}
        <p className="ui-state-body">Not available:</p>
        <ul className="ui-state-list">
          {missing.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/** The engines did not have enough evidence to conclude. Says so instead of showing a guess. */
export function InsufficientEvidenceState({
  title = "Not enough evidence to conclude",
  reason,
  children,
}: {
  title?: string;
  /** Why, in plain words (e.g. "No CGHS row matches this line"). */
  reason: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="ui-state ui-state-insufficient" role="status">
      <FileQuestion size={22} aria-hidden="true" />
      <div>
        <p className="ui-state-title">{title}</p>
        <p className="ui-state-body">{reason}</p>
        {children && <div className="ui-state-body">{children}</div>}
        <p className="ui-state-note">No figure is shown, and nothing is guessed.</p>
      </div>
    </div>
  );
}
