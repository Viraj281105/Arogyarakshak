import type { ClinicalStatement, EvidenceItem, SafetyEscalation } from "../../../lib/clinical";
import type { Explanation } from "../../../lib/explanation";

// --- Clinical plausibility (ADR-011): bounded, never a necessity determination ---
export interface PlausibilityResponse {
  case_id: string;
  assessment: {
    status: "PLAUSIBLE" | "INSUFFICIENT_INFORMATION" | "POTENTIAL_INCONSISTENCY" | "CLINICAL_REVIEW_RECOMMENDED";
    summary: string;
    disclaimer: string;
    clinical_review_required: boolean;
    review_reasons: string[];
    evidence_used: EvidenceItem[];
    not_assessed_items: string[];
    conflicting_items?: string[];
    excluded_administrative_items: string[];
    coverage: "FULL" | "PARTIAL" | "NONE";
    references: { name: string; type: string; version: string; icd10_code: string; diagnosis_label: string }[];
    guideline_citations: unknown[];
    guideline_note: string;
    method: string;
    safety_check_status?: "EVALUATED" | "UNAVAILABLE";
  };
  safety_escalations: SafetyEscalation[];
  safety_check?: { status: "EVALUATED" | "UNAVAILABLE"; note: string | null };
  clinical_review: { required: boolean; status: string; human_statement_exists: boolean };
}

// --- API Response Types (matching backend AuditResponse schema) ---
export type AuditItemStatus =
  | "overcharged"
  | "within_benchmark"
  | "bundled"
  | "not_benchmarked";

export interface AuditResultItem {
  item_name: string;
  charged: number;
  // null when the item has no CGHS counterpart — it must never render as "Fair".
  cghs_benchmark: number | null;
  deviation_percentage: number;
  is_deviation: boolean;
  benchmarked: boolean;
  status: AuditItemStatus;
  /** What the reference covers for this line, e.g. "₹4,500 per day × 3 days". */
  benchmark_basis?: string | null;
  /** Why a matched line was not compared (e.g. a per-day rate and no day count). */
  not_benchmarked_reason?: string | null;
  /** "Why am I seeing this?" trail (ADR-017). */
  explanation?: Explanation | null;
}

export interface AuditResponse {
  case_id: string;
  total_charged: number;
  total_benchmark: number;
  benchmarked_charged: number;
  potential_savings: number;
  deviations_count: number;
  benchmarked_count: number;
  unmatched_count: number;
  unmatched_amount: number;
  audit_items: AuditResultItem[];
}

// --- Appeal Response Types (matching backend AppealResponse schema, #18/#66) ---
export interface AppealResponse {
  case_id: string;
  appeal_letter: string;
  scorecard: { overall_score: number; status: string; confidence_estimate: number };
  status: string;
  denial_facts_extracted: boolean;
  llm_backed: boolean;
  consensus: { final_verdict: string; weighted_score: number; is_unanimous: boolean };
  revision_count: number;
  document_sha256: string;
  pdf_download_url: string;
  language: string;
  // ADR-011: attributed human statements, appended verbatim — never LLM-written.
  human_clinical_statement_attached: boolean;
  clinical_statements: ClinicalStatement[];
  clinical_annex: string;
  clinical_statement_notice: string;
}
