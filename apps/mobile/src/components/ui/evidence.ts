// The single evidence vocabulary (Wave 3, architecture doc section 5), mobile copy. Pure data, no
// react-native import, so it is unit-tested. It mirrors apps/web/app/components/ui/evidence.ts; the
// test tests/primitives.test.ts fails if the states, labels or citation mapping drift apart.
// Token names: evidence<State>Fg/Bg/Border in the generated palette (AA-checked in both themes).

export const EVIDENCE_STATES = [
  'verified',
  'provisional',
  'unevaluated',
  'insufficient-evidence',
  'ai-generated',
  'rule-engine',
  'user-provided',
  'external',
] as const;

export type EvidenceState = (typeof EVIDENCE_STATES)[number];

/** Visible label (the badge never relies on colour alone) and the longer meaning (accessibility hint). */
export const EVIDENCE_COPY: Record<EvidenceState, { label: string; meaning: string }> = {
  verified: {
    label: 'Verified',
    meaning: 'Checked against the cited source: every figure in the statement appears in it.',
  },
  provisional: {
    label: 'Provisional',
    meaning: 'Partly checked: the source is attributed, but not every figure could be confirmed.',
  },
  unevaluated: {
    label: 'Not evaluated',
    meaning: 'Not checked yet, or it cannot be checked automatically.',
  },
  'insufficient-evidence': {
    label: 'Insufficient evidence',
    meaning: 'The available source does not support this statement, so no conclusion is drawn from it.',
  },
  'ai-generated': {
    label: 'AI-generated',
    meaning: 'Written by a language model. Read it as a draft, not as a finding.',
  },
  'rule-engine': {
    label: 'Rule engine',
    meaning: 'Computed by a deterministic rule from published reference data.',
  },
  'user-provided': {
    label: 'You provided',
    meaning: 'Entered or confirmed by you; not independently checked.',
  },
  external: {
    label: 'External source',
    meaning: 'Taken from a public reference (for example CGHS, NPPA or IRDAI), quoted as published.',
  },
};

/** Wave 2 citation statuses from `schemesetu.citations.verify_citation`. */
export type CitationStatus = 'supported' | 'scheme_only' | 'unsupported' | 'uncheckable';

/**
 * How a Wave 2 citation status is shown (docs/design/wave3-components.md, section 2).
 * supported -> verified; scheme_only -> provisional; unsupported -> insufficient-evidence;
 * uncheckable -> unevaluated (never verified).
 */
export const CITATION_TO_EVIDENCE: Record<CitationStatus, EvidenceState> = {
  supported: 'verified',
  scheme_only: 'provisional',
  unsupported: 'insufficient-evidence',
  uncheckable: 'unevaluated',
};

/** Maps a citation status string from an API response; unknown values are never shown as verified. */
export function evidenceFromCitation(status: string): EvidenceState {
  return Object.prototype.hasOwnProperty.call(CITATION_TO_EVIDENCE, status)
    ? CITATION_TO_EVIDENCE[status as CitationStatus]
    : 'unevaluated';
}

/** Palette key prefix for a state: 'insufficient-evidence' -> 'evidenceInsufficientEvidence'. */
export function evidenceTokenPrefix(state: EvidenceState): string {
  return `evidence${state
    .split('-')
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join('')}`;
}
