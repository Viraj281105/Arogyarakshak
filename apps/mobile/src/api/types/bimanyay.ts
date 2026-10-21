/** BimaNyay: denial analysis and grievance timeline types. Mirrors the FastAPI schemas in apps/api. */
import type { Explanation } from '../../services/explanation';

// --- BimaNyay ---
export interface BimaNyayAnalysisRequest {
  policy_number: string;
  insurer_name: string;
  policy_age_years: number;
  claimed_amount: number;
  denied_or_deducted_amount: number;
  denied_amount?: number;
  denial_category: string;
  denial_reason_raw: string;
  diagnosis: string;
}

export interface RegulatoryViolation {
  statute_or_circular: string;
  clause_reference: string;
  violation_summary: string;
  legal_remedy: string;
}

export interface BimaNyayAnalysisResponse {
  is_wrongful_denial: boolean;
  reversal_probability_score: number;
  /** Always "HEURISTIC_PRIOR_NOT_HISTORICAL": a rule prior, not a probability from past outcomes. */
  probability_basis?: 'HEURISTIC_PRIOR_NOT_HISTORICAL';
  primary_dispute_grounds: string;
  regulatory_violations: RegulatoryViolation[];
  level_1_gro_appeal: string;
  level_2_bimabharosa_text: string;
  level_3_ombudsman_grounds: string;
  /** ADR-011: whether the denial turns on clinical judgment. Never an outcome prediction. */
  clinical_review?: {
    requires_clinical_interpretation: boolean;
    reasons: string[];
    suggested_clinical_question: string | null;
    note: string;
  } | null;
}

export interface BimaNyayTimelineRequest {
  insurer_name: string;
  date_initiated: string;
  claim_number?: string;
  current_tier: string;
}

export interface GrievanceTimelineEvent {
  tier: string;
  title: string;
  deadline_date: string;
  status: string;
  instructions: string;
  explanation?: Explanation | null;
}

export interface BimaNyayTimelineResponse {
  claim_number: string | null;
  insurer_name: string;
  date_initiated: string;
  current_tier: string;
  timeline_events: GrievanceTimelineEvent[];
}
