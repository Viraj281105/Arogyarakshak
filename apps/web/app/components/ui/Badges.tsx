import React from "react";
import { EVIDENCE_ICONS } from "../../shell/icons/evidenceIcons";
import { EVIDENCE_COPY, type EvidenceState } from "./evidence";

/**
 * The one evidence badge (eight states). Always shows a text label next to its icon, never colour
 * alone; `title` carries the longer meaning. Server-safe (no hooks).
 */
export function EvidenceBadge({
  state,
  label,
  size = "md",
  showMeaning = false,
}: {
  state: EvidenceState;
  /** Override the visible label (e.g. a translated string); defaults to the vocabulary label. */
  label?: string;
  size?: "sm" | "md";
  /** Render the meaning as visible text after the badge (for legends). */
  showMeaning?: boolean;
}) {
  const Icon = EVIDENCE_ICONS[state];
  const copy = EVIDENCE_COPY[state];
  return (
    <span className="ui-evidence-wrap">
      <span className={`ui-badge ui-evidence ui-evidence-${state} ui-badge-${size}`} title={copy.meaning} data-evidence={state}>
        <Icon size={size === "sm" ? 12 : 14} aria-hidden="true" />
        <span>{label ?? copy.label}</span>
      </span>
      {showMeaning && <span className="ui-evidence-meaning">{copy.meaning}</span>}
    </span>
  );
}

export type StatusTone = "success" | "warning" | "danger" | "info" | "neutral";

/** A general status chip (process state, not evidence). Text is required; tone only reinforces it. */
export function StatusBadge({ tone, children }: { tone: StatusTone; children: React.ReactNode }) {
  return (
    <span className={`ui-badge ui-status ui-status-${tone}`}>
      <span className="ui-status-dot" aria-hidden="true" />
      {children}
    </span>
  );
}

/** Pure: bucket a 0..1 confidence for its visible word. Values outside 0..1 are clamped. */
export function confidenceBucket(value: number): { pct: number; word: "High" | "Medium" | "Low" } {
  const v = Math.min(1, Math.max(0, Number.isFinite(value) ? value : 0));
  const pct = Math.round(v * 100);
  return { pct, word: v >= 0.85 ? "High" : v >= 0.6 ? "Medium" : "Low" };
}

/**
 * Model or extraction confidence as a meter with its number and a word. It describes how sure
 * the extractor was, not whether the value is correct; `source` says who produced the number.
 */
export function ConfidenceIndicator({
  value,
  label = "Confidence",
  source,
}: {
  /** 0..1, as returned by the API. */
  value: number;
  label?: string;
  /** Who computed it, e.g. "OCR engine". Required so a bare number never floats free. */
  source: string;
}) {
  const { pct, word } = confidenceBucket(value);
  return (
    <span className={`ui-confidence ui-confidence-${word.toLowerCase()}`}>
      <span className="ui-confidence-label">{label}</span>
      <meter className="ui-confidence-meter" min={0} max={100} low={60} high={85} optimum={100} value={pct} aria-label={`${label}: ${pct}%`} />
      <span className="ui-confidence-value code-tabular">
        {pct}% · {word}
      </span>
      <span className="ui-confidence-source">({source})</span>
    </span>
  );
}

/**
 * A single headline figure. `basis` is mandatory: a figure is either an estimate or verified
 * against a source, and the card says which in words. `source` and `period` keep it honest.
 */
export function MetricCard({
  label,
  value,
  unit,
  basis,
  source,
  period,
  note,
}: {
  label: string;
  /** Pre-formatted value (use Intl.NumberFormat('en-IN') upstream). */
  value: string;
  unit?: string;
  basis: "estimate" | "verified";
  source: string;
  period?: string;
  note?: React.ReactNode;
}) {
  return (
    <div className={`ui-metric ui-metric--${basis}`}>
      <div className="ui-metric-head">
        <span className="ui-metric-label">{label}</span>
        {basis === "verified" ? <EvidenceBadge state="verified" size="sm" /> : <span className="ui-badge ui-badge-sm ui-estimate-badge">Estimate</span>}
      </div>
      <p className="ui-metric-value code-tabular">
        {value}
        {unit && <span className="ui-metric-unit"> {unit}</span>}
      </p>
      <p className="ui-metric-meta">
        Source: {source}
        {period && <> · {period}</>}
      </p>
      {note && <div className="ui-metric-note">{note}</div>}
    </div>
  );
}
