import { msg } from "../../i18n/format";
// The single evidence vocabulary (Wave 3, architecture doc section 5). Pure data, no JSX, so it is
// unit-tested and usable from Server and Client Components. Token names: evidence-<state>-fg/bg/border
// in packages/design-tokens/tokens.json (AA-checked in both themes).

export const EVIDENCE_STATES = [
  "verified",
  "provisional",
  "unevaluated",
  "insufficient-evidence",
  "ai-generated",
  "human-reviewed",
  "rule-engine",
  "user-provided",
  "external",
] as const;

export type EvidenceState = (typeof EVIDENCE_STATES)[number];

/** Visible label (the badge never relies on colour alone) and the longer meaning for tooltips/docs. */
export const EVIDENCE_COPY: Record<EvidenceState, { label: string; meaning: string }> = {
  verified: {
    label: msg("Verified"),
    meaning: msg("Checked against the cited source: every figure in the statement appears in it."),
  },
  provisional: {
    label: msg("Provisional"),
    meaning: msg("Partly checked: the source is attributed, but not every figure could be confirmed."),
  },
  unevaluated: {
    label: msg("Not evaluated"),
    meaning: msg("Not checked yet, or it cannot be checked automatically."),
  },
  "insufficient-evidence": {
    label: msg("Insufficient evidence"),
    meaning: msg("The available source does not support this statement, so no conclusion is drawn from it."),
  },
  "ai-generated": {
    label: msg("AI-generated"),
    meaning: msg("Written by a language model. Read it as a draft, not as a finding."),
  },
  "human-reviewed": {
    label: msg("Human-reviewed"),
    meaning: msg("Read and finalised by a named reviewer. Reviewer credentials are self-declared unless stated otherwise."),
  },
  "rule-engine": {
    label: msg("Rule engine"),
    meaning: msg("Computed by a deterministic rule from published reference data."),
  },
  "user-provided": {
    label: msg("You provided"),
    meaning: msg("Entered or confirmed by you; not independently checked."),
  },
  external: {
    label: msg("External source"),
    meaning: msg("Taken from a public reference (for example CGHS, NPPA or IRDAI), quoted as published."),
  },
};

/** Wave 2 citation statuses from `schemesetu.citations.verify_citation`. */
export type CitationStatus = "supported" | "scheme_only" | "unsupported" | "uncheckable";

/**
 * How a Wave 2 citation status is shown. Documented in docs/design/wave3-components.md.
 * - supported: every figure was found in the cited span -> verified.
 * - scheme_only: the scheme is attributed but no figure was verified -> provisional.
 * - unsupported: the span does not support the sentence (the backend drops it) -> insufficient-evidence.
 * - uncheckable: the figure cannot be checked (words, unknown unit) -> unevaluated, never verified.
 */
export const CITATION_TO_EVIDENCE: Record<CitationStatus, EvidenceState> = {
  supported: "verified",
  scheme_only: "provisional",
  unsupported: "insufficient-evidence",
  uncheckable: "unevaluated",
};

/** Maps a citation status string from an API response; unknown values are never shown as verified. */
export function evidenceFromCitation(status: string): EvidenceState {
  return Object.hasOwn(CITATION_TO_EVIDENCE, status)
    ? CITATION_TO_EVIDENCE[status as CitationStatus]
    : "unevaluated";
}
