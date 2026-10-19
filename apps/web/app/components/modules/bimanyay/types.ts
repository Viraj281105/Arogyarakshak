import type { ClinicalStatement } from "../../../lib/clinical";
import type { Explanation } from "../../../lib/explanation";

// ADR-011: whether the denial turns on clinical judgment. Never an outcome prediction.
export interface ClinicalReviewTrigger {
  requires_clinical_interpretation: boolean;
  reasons: string[];
  suggested_clinical_question: string | null;
  note: string;
}

export interface ClinicalStatementsResponse {
  human_clinical_statement_attached: boolean;
  statements: ClinicalStatement[];
  annex_text: string;
}

// --- API Response Types (matching backend Pydantic schemas) ---
export interface RegulatoryViolation {
  statute_or_circular: string;
  clause_reference: string;
  violation_summary: string;
  legal_remedy: string;
}

export interface DisputeAuditResult {
  is_wrongful_denial: boolean;
  reversal_probability_score: number;
  /** "HEURISTIC_PRIOR_NOT_HISTORICAL": a rule prior, not a probability from past outcomes. */
  probability_basis?: string;
  primary_dispute_grounds: string;
  regulatory_violations: RegulatoryViolation[];
  level_1_gro_appeal: string;
  level_2_bimabharosa_text: string;
  level_3_ombudsman_grounds: string;
  clinical_review?: ClinicalReviewTrigger | null;
}

export interface GrievanceTimelineEvent {
  tier: string;
  title: string;
  deadline_date: string;
  status: string;
  instructions: string;
  /** "Why am I seeing this?" trail (ADR-017). */
  explanation?: Explanation | null;
}

export interface GrievanceTrackerResponse {
  claim_number: string | null;
  insurer_name: string;
  date_initiated: string;
  current_tier: string;
  timeline_events: GrievanceTimelineEvent[];
}
