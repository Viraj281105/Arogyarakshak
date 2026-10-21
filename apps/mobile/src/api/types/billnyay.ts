/** BillNyay: CGHS audit and the 5-agent appeal (#18/#39/#65/#66/#68). Mirrors the FastAPI schemas in apps/api. */
import type { Explanation } from '../../services/explanation';
import type { ClinicalStatement } from './clinical';

// --- BillNyay ---
export type BillNyayAuditItemStatus =
  | 'overcharged'
  | 'within_benchmark'
  | 'bundled'
  | 'not_benchmarked';

export interface BillNyayAuditItem {
  item_name: string;
  charged: number;
  // null when the item has no CGHS counterpart — must never be shown as "Fair".
  cghs_benchmark: number | null;
  deviation_percentage: number;
  is_deviation: boolean;
  benchmarked: boolean;
  status: BillNyayAuditItemStatus;
  /** What the reference covers, e.g. "₹4,500 per day × 3 days" (billnyay.rate_basis). */
  benchmark_basis?: string | null;
  /** Why a matched line was not compared (e.g. a per-day rate and no day count). */
  not_benchmarked_reason?: string | null;
  /** "Why am I seeing this?" trail (ADR-017). */
  explanation?: Explanation | null;
}

export interface BillNyayAuditResponse {
  case_id: string;
  total_charged: number;
  total_benchmark: number;
  benchmarked_charged: number;
  potential_savings: number;
  deviations_count: number;
  benchmarked_count: number;
  unmatched_count: number;
  unmatched_amount: number;
  audit_items: BillNyayAuditItem[];
}

// --- BillNyay appeal (5-agent pipeline, #18/#39/#65/#66/#68) ---
export interface BillNyayAppealScorecard {
  overall_score: number;
  status: string;
  confidence_estimate: number;
  issues: { severity: string; description: string }[];
}

export interface BillNyayAppealConsensus {
  final_verdict: string;
  weighted_score: number;
  is_unanimous: boolean;
  requires_judge_override: boolean;
}

export interface BillNyayAppealResponse {
  case_id: string;
  appeal_letter: string;
  scorecard: BillNyayAppealScorecard;
  status: string;
  /** False when the Auditor could not extract denial facts from the document — the
   * letter is then built on "Not specified in the supplied documents" placeholders. */
  denial_facts_extracted: boolean;
  /** False when GROQ_API_KEY is unset: a static statutory template, not an LLM draft
   * grounded in this case's actual denial. Must be disclosed to the user, never hidden. */
  llm_backed: boolean;
  consensus: BillNyayAppealConsensus;
  revision_count: number;
  document_sha256: string;
  pdf_download_url: string;
  language: string;
  /** ADR-011: attributed human statements appended verbatim — never LLM-written. */
  human_clinical_statement_attached: boolean;
  clinical_statements: ClinicalStatement[];
  clinical_annex: string;
  /** Patient-facing only; never part of the insurer-facing PDF. */
  clinical_statement_notice: string;
}
