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
  /** "processing", or "duplicate" when this exact document was already ingested into the case. */
  status: string;
  message: string;
  case_id: string;
  filename: string;
}

// --- Kadi entity resolution (#31, #88) ---
export type ResolutionSignalStatus = 'AVAILABLE' | 'UNAVAILABLE' | 'NOT_APPLICABLE';

export interface ResolutionSignal {
  signal: 'lexical' | 'phonetic' | 'semantic';
  status: ResolutionSignalStatus;
  score: number | null;
  detail: string;
}

export interface ResolutionDecision {
  id: string;
  entity_type: string;
  action: 'MERGE' | 'ASK';
  status: string;
  source: string;
  /** Similarity evidence in [0, 1] — not a probability. */
  confidence: number;
  mention_name: string | null;
  mention_entity_id: string | null;
  candidate_entity_id: string;
  candidate_name: string;
  signals: ResolutionSignal[];
  reasons: string[];
  feedback_same_entity: boolean | null;
}

export interface ResolutionFeedbackResponse {
  decision: ResolutionDecision;
  calibration: {
    scope: string;
    status: 'CALIBRATED' | 'INSUFFICIENT_EVIDENCE';
    merge_threshold: number;
    ask_threshold: number;
    sample_count: number;
    reasons: string[];
  }[];
}

// --- SchemeSetu consent-bounded income profile (#92) ---
export interface IncomeProfileRequest {
  annual_income_inr: number;
  state: string;
}

export interface IncomeProfileResponse {
  case_id: string;
  annual_income_inr: number;
  state: string;
  trigger: {
    status: 'FIRE' | 'NO_CHANGE' | 'INSUFFICIENT_EVIDENCE';
    reason: string;
    /** Income alone never triggers a run: no evaluated scheme defines an income ceiling. */
    income_role: 'NON_DETERMINATIVE';
  };
  background_eligibility: 'queued' | 'not_ready' | 'not_triggered';
  missing_context: string[];
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
  /** Optional fields fall back to entities extracted from the case, never to defaults. */
  hospital_name?: string;
  treatment_plan?: string;
  diagnosis?: string;
  estimated_cost?: number;
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
  /** Always "HEURISTIC_PRIOR_NOT_HISTORICAL": a rule prior, not a probability from past outcomes. */
  probability_basis?: 'HEURISTIC_PRIOR_NOT_HISTORICAL';
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

export interface SchemeSource {
  url: string;
  document: string;
  publisher: string;
  date: string | null;
}

export interface SchemeResult {
  scheme_name: string;
  estimated_eligibility: 'eligible' | 'ineligible' | 'ambiguous';
  reason: string;
  /** How to claim when eligible; how to verify when ambiguous. */
  claim_guide_steps: string[];
  criteria_evaluated: string[];
  /** Recorded but never decisive: neither scheme defines an official income ceiling. */
  non_determinative_factors: string[];
  /** Eligibility factors the engine does not check; the result stays provisional. */
  criteria_not_evaluated: string[];
  is_provisional: boolean;
  criteria_provenance: string;
  sources: SchemeSource[];
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
  /** Provenance of the ceiling price — the reference list is a curated subset. */
  data_source: string;
  reference_entry_count: number;
}

export interface TranslateInstructionsRequest {
  instructions: string;
  language: 'en' | 'hi' | 'mr';
}

export interface TranslatedInstruction {
  token: string;
  recognized: boolean;
  meaning_en: string;
  translated: string;
}

export interface PrescriptionTranslationResponse {
  original_text: string;
  language: string;
  instructions: TranslatedInstruction[];
  unrecognized_tokens: string[];
}

export interface ApiError {
  message: string;
  detail?: string;
  statusCode?: number;
}
