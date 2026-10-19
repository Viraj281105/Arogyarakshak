/**
 * "Why am I seeing this?" (ADR-017) — plain-text rendering of the server's explanation.
 * Mirrors kadi.explanation.render_plain_text: only what the server recorded is shown, and
 * an unrecorded value reads "not recorded". English-first; hi/mr copy for the fixed labels
 * is NEEDS NATIVE-SPEAKER QA and not yet added on mobile.
 */
export interface ExplanationFact {
  label: string;
  value: string | null;
}

export interface Explanation {
  finding_type: string;
  headline: string;
  evidence: {
    label: string;
    value: string | null;
    provenance: string;
    document: string | null;
    source_text: string | null;
  }[];
  rules: { kind: string; name: string; facts: ExplanationFact[]; source: string | null }[];
  trust: { code: string; label: string; detail: string | null };
  undetermined: { code: string; reason: string }[];
  not_recorded: string[];
  generated_by: string;
  disclaimer: string;
}

export const NOT_RECORDED = 'not recorded';

const PROVENANCE: Record<string, string> = {
  OCR_EXTRACTED: 'read from your document',
  LLM_NORMALISED: 'wording may have been normalised by the extractor',
  HUMAN_REVIEWED: 'reviewed by a human',
  USER_ENTERED: 'entered by you',
  REFERENCE_DATA: 'public reference table',
  RULE_COMPUTED: 'computed by a fixed rule',
  NOT_RECORDED: 'origin not recorded',
};

const NEEDS_DOCUMENT = new Set(['OCR_EXTRACTED', 'LLM_NORMALISED']);

export function explanationToText(e: Explanation): string {
  const lines: string[] = [e.headline, '', `Confidence: ${e.trust.label}${e.trust.detail ? ` — ${e.trust.detail}` : ''}`];
  if (e.evidence.length > 0) {
    lines.push('', 'Source evidence:');
    for (const ev of e.evidence) {
      const doc = NEEDS_DOCUMENT.has(ev.provenance) ? ` · document: ${ev.document ?? NOT_RECORDED}` : '';
      const src = ev.source_text ? ` · read from “${ev.source_text}”` : '';
      lines.push(`• ${ev.label}: ${ev.value ?? NOT_RECORDED} (${PROVENANCE[ev.provenance] ?? PROVENANCE.NOT_RECORDED})${doc}${src}`);
    }
  }
  if (e.rules.length > 0) {
    lines.push('', 'Rule or reference used:');
    for (const r of e.rules) {
      lines.push(`• ${r.name}${r.source ? ` (${r.source})` : ''}`);
      for (const f of r.facts) lines.push(`    ${f.label}: ${f.value ?? NOT_RECORDED}`);
    }
  }
  if (e.undetermined.length > 0) {
    lines.push('', 'What could not be determined:');
    for (const u of e.undetermined) lines.push(`• ${u.reason}`);
  }
  lines.push('', 'Written by fixed rules from stored data — no AI model wrote this explanation.', e.disclaimer);
  return lines.join('\n');
}
