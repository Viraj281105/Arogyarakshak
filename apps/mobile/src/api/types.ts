/**
 * ArogyaRakshak API Request & Response Types
 * Aligned strictly with FastAPI schemas in apps/api/app/api/v1/endpoints/
 */

// Mirrors the backend CaseResponse exactly. `case_id` and `user_id` were previously
// declared here but the API returns neither, so any code branching on them was dead.
export interface CaseResponse {
  id: string;
  status: string;
  consent_opt_in: boolean;
  total_charged: number;
  created_at: string;
}

export interface UploadResponse {
  status: string;
  message: string;
  case_id: string;
  filename: string;
}

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

// --- DaaviSetu ---
export interface DaaviSetuClaimRequest {
  policy_number: string;
  patient_name: string;
  hospital_name?: string;
  treatment_plan?: string;
  diagnosis?: string;
}

export interface DaaviSetuFormData {
  policy_number: string;
  patient_name: string;
  hospital_name: string;
  diagnosis: string;
  estimated_cost: number;
  treatment_plan: string;
}

export interface DaaviSetuClaimResponse {
  claim_id: string;
  form_data: DaaviSetuFormData;
  form_filled_pdf_path: string | null;
  status: string;
}

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
  primary_dispute_grounds: string;
  regulatory_violations: RegulatoryViolation[];
  level_1_gro_appeal: string;
  level_2_bimabharosa_text: string;
  level_3_ombudsman_grounds: string;
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
}

export interface BimaNyayTimelineResponse {
  claim_number: string | null;
  insurer_name: string;
  date_initiated: string;
  current_tier: string;
  timeline_events: GrievanceTimelineEvent[];
}

// --- SchemeSetu ---
export interface SchemeSetuEligibilityRequest {
  income: number;
  location_state: string;
  category: string;
  medical_need: string;
}

export interface SchemeResult {
  scheme_name: string;
  estimated_eligibility: string;
  confidence_score: number;
  reason: string;
  claim_guide_steps: string[];
}

// --- DawaCheck ---
export interface DawaCheckBenchmarkRequest {
  brand_name: string;
  mrp: number;
}

export interface DawaCheckBenchmarkResponse {
  brand_name: string;
  active_ingredient: string;
  mrp: number;
  nppa_ceiling_price: number;
  is_overcharged: boolean;
  deviation_percentage: number;
  generic_substitute_available: boolean;
  generic_substitute_store_info: string;
}

export interface ApiError {
  message: string;
  detail?: string;
  statusCode?: number;
}
