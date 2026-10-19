import type { Language } from "../translations";
import { EXPLAIN_STRINGS } from "./explainStrings";

/** Mirrors `kadi.explanation.Explanation` (ADR-015). Every field is produced by
 * deterministic server code from stored data; a missing value is `null`, never a guess. */
export interface Fact {
  label: string;
  value: string | null;
}
export interface EvidenceItem {
  label: string;
  value: string | null;
  provenance: string;
  document: string | null;
  source_text: string | null;
}
export interface RuleUsed {
  kind: string;
  name: string;
  facts: Fact[];
  source: string | null;
}
export interface Explanation {
  finding_type: "BILLNYAY_LINE" | "DAWACHECK_MEDICINE" | "DAAVISETU_ITEM" | "BIMANYAY_DEADLINE";
  headline: string;
  evidence: EvidenceItem[];
  rules: RuleUsed[];
  trust: { code: string; label: string; detail: string | null };
  undetermined: { code: string; reason: string }[];
  not_recorded: string[];
  generated_by: string;
  disclaimer: string;
}

const NEEDS_DOCUMENT = new Set(["OCR_EXTRACTED", "LLM_NORMALISED"]);

export interface ExplainView {
  headline: string;
  evidence: { label: string; value: string; provenance: string; document: string | null; sourceText: string | null }[];
  rules: { name: string; source: string | null; facts: { label: string; value: string; recorded: boolean }[] }[];
  trust: { label: string; detail: string | null };
  undetermined: string[];
  notRecorded: string[];
}

/** Turns the server's explanation into display rows. Anything the server did not record is
 * shown as the localised "not recorded" — never blank and never filled in. */
export function describeExplanation(e: Explanation, lang: Language = "en"): ExplainView {
  const s = EXPLAIN_STRINGS[lang] ?? EXPLAIN_STRINGS.en;
  return {
    headline: e.headline,
    evidence: e.evidence.map((ev) => ({
      label: ev.label,
      value: ev.value ?? s.notRecorded,
      provenance: s.provenance[ev.provenance] ?? s.provenance.NOT_RECORDED,
      document: NEEDS_DOCUMENT.has(ev.provenance) ? ev.document ?? s.notRecorded : ev.document,
      sourceText: ev.source_text,
    })),
    rules: e.rules.map((r) => ({
      name: r.name,
      source: r.source,
      facts: r.facts.map((f) => ({ label: f.label, value: f.value ?? s.notRecorded, recorded: f.value !== null })),
    })),
    trust: { label: e.trust.label, detail: e.trust.detail },
    undetermined: e.undetermined.map((u) => u.reason),
    notRecorded: e.not_recorded,
  };
}
