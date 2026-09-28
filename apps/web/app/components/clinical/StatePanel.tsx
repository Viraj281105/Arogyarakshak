"use client";

import React from "react";

type Kind = "loading" | "empty" | "error" | "warning" | "success" | "info";

const ICON: Record<Exclude<Kind, "loading">, string> = {
  empty: "ⓘ",
  error: "⚠️",
  warning: "⚠️",
  success: "✓",
  info: "ⓘ",
};

const CLASS: Record<Kind, string> = {
  loading: "state-panel",
  empty: "state-panel",
  error: "state-panel is-error",
  warning: "state-panel is-warning",
  success: "state-panel is-success",
  info: "state-panel is-info",
};

/**
 * One consistent shape for loading, empty, error, warning and success states, so every
 * module panel communicates them the same way. An error always offers a retry when the
 * caller can retry.
 */
export const StatePanel: React.FC<{
  kind: Kind;
  children: React.ReactNode;
  onRetry?: () => void;
  retryLabel?: string;
}> = ({ kind, children, onRetry, retryLabel = "Try again" }) => (
  <div className={CLASS[kind]} role={kind === "error" || kind === "warning" ? "alert" : "status"} aria-live="polite">
    {kind === "loading" ? <span className="spinner" aria-hidden="true" /> : <span aria-hidden="true">{ICON[kind]}</span>}
    <div style={{ flex: 1, minWidth: 0 }}>
      {children}
      {onRetry && (
        <div className="state-actions">
          <button type="button" className="btn btn-secondary btn-compact" onClick={onRetry}>
            {retryLabel}
          </button>
        </div>
      )}
    </div>
  </div>
);
