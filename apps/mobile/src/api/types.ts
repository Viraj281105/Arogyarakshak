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

export interface CaseCreatedResponse extends CaseResponse {
  /** ADR-009: shown exactly once, here. Required on every later case-scoped request. */
  access_token: string;
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
  /** What the reference covers, e.g. "₹4,500 per day × 3 days" (billnyay.rate_basis). */
  benchmark_basis?: string | null;
  /** Why a matched line was not compared (e.g. a per-day rate and no day count). */
  not_benchmarked_reason?: string | null;
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
  /** The amount paid, on the basis in `price_basis`. */
  mrp: number;
  price_basis?: 'PER_UNIT' | 'PER_STRIP' | 'PER_PACK' | 'LINE_TOTAL' | 'UNKNOWN';
  units_per_pack?: number;
  quantity?: number;
}

export interface DawaCheckBenchmarkResponse {
  brand_name: string;
  active_ingredient: string;
  /** Amount as billed/entered (see price_basis); the per-unit figure is billed_unit_price. */
  mrp: number;
  /** Ceiling per unit_label (one tablet/capsule/vial). */
  nppa_ceiling_price: number;
  /** null when no comparison could be made (comparison_status CANNOT_COMPARE). */
  is_overcharged: boolean | null;
  deviation_percentage: number | null;
  comparison_status?: 'COMPARED' | 'CANNOT_COMPARE';
  price_basis?: 'PER_UNIT' | 'PER_STRIP' | 'PER_PACK' | 'LINE_TOTAL' | 'UNKNOWN';
  price_basis_label?: string;
  basis_source?: string;
  basis_evidence?: string | null;
  billed_unit_price?: number | null;
  unit_label?: string;
  comparison_note?: string | null;
  generic_substitute_available: boolean;
  generic_substitute_store_info: string;
  /** Provenance of the ceiling price — the reference list is a curated subset. */
  data_source: string;
  reference_entry_count: number;
}

/** One row of GET /dawacheck/cases/{id}/benchmark — the server's trust decision per medicine. */
export interface CaseMedicineBenchmark {
  entity_id: string;
  brand_name: string;
  benchmark: DawaCheckBenchmarkResponse | null;
  note: string | null;
  name_provenance: Provenance;
  transcription_task_id: string | null;
  transcription_status: string | null;
  trust: { state?: string; label?: string; benchmarkable?: boolean; reasons?: string[] };
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

// --- ADR-011: clinical review, safety governance, human OCR resolution ---
export type Provenance = 'AI_DERIVED' | 'HUMAN_REVIEWED' | 'HUMAN_AUTHORED' | 'EXTERNAL_SOURCE' | 'PATIENT_PROVIDED';

export interface ReviewerProfile {
  id: string;
  name: string;
  designation: string | null;
  category: string;
  category_label: string;
  specialty: string | null;
  registration_number: string | null;
  registration_authority: string | null;
  verification_status: 'UNVERIFIED' | 'SELF_DECLARED' | 'DEMO_VERIFIED' | 'EXTERNALLY_VERIFIED';
  /** The only verification wording the app may show — never upgraded client-side. */
  verification_label: string;
  affiliation: string | null;
}

export interface ReviewerSnapshot extends Omit<ReviewerProfile, 'id'> {
  reviewer_id: string;
}

export interface EvidenceRef {
  item_id: string;
  kind: string;
  label: string;
  provenance: Provenance;
  source: string;
}

export interface ClinicalStatement {
  statement_id: string;
  statement_version: number;
  status: 'DRAFT' | 'UNDER_REVIEW' | 'FINALIZED' | 'SUPERSEDED' | 'WITHDRAWN';
  provenance: Provenance;
  clinical_question: string;
  evidence_reviewed: EvidenceRef[];
  reviewer_statement: string;
  limitations: string;
  coi_category: string;
  coi_label: string | null;
  coi_disclosure: string | null;
  reviewer_snapshot: ReviewerSnapshot | null;
  finalized_at: string | null;
  content_sha256: string | null;
  withdrawn_reason: string | null;
}

export interface FactDecisionView {
  fact_id: string;
  fact_key: string;
  fact_question: string;
  decision: 'PENDING' | 'CONFIRMED' | 'REJECTED' | 'CANNOT_DETERMINE';
  coi_label: string | null;
}

export interface CaseClinicalReview {
  review_id: string;
  source_module: string;
  review_type: 'CLINICAL_STATEMENT' | 'FACT_CONFIRMATION';
  status: 'REQUESTED' | 'ASSIGNED' | 'IN_REVIEW' | 'COMPLETED' | 'DECLINED' | 'CANCELLED';
  assigned_reviewer: ReviewerProfile | null;
  coi_label: string | null;
  coi_disclosure: string | null;
  evidence_shared: EvidenceRef[];
  human_statement_exists: boolean;
  current_statement: ClinicalStatement | null;
  statement_history: ClinicalStatement[];
  draft_in_progress: boolean;
  facts: FactDecisionView[];
}

export interface ClinicalReviewRequest {
  source_module: 'billnyay' | 'bimanyay' | 'kadi';
  clinical_question?: string;
  trigger?: 'MANUAL' | 'PLAUSIBILITY_FLAG' | 'DENIAL_CATEGORY' | 'SAFETY_RULE';
  insurer_name?: string;
  /** Must be the patient's explicit choice for this request — never defaulted to true. */
  share_with_reviewer_consent: boolean;
}

export interface SafetyEscalation {
  rule_id: string;
  rule_version: number;
  title: string;
  severity: 'URGENT' | 'ADVISORY';
  message: string;
  matched_terms: string[];
  source: { name: string; version: string | null; section: string | null };
  limitations: string[];
  disclaimer: string;
}

export interface SafetyEvaluation {
  /** UNAVAILABLE: the rules could not be evaluated — never render as "no escalation". */
  status?: 'EVALUATED' | 'UNAVAILABLE';
  active_rule_count?: number | null;
  escalations: SafetyEscalation[];
  disclaimer: string;
  coverage_note: string;
}

export interface PlausibilityResponse {
  assessment: {
    status: 'PLAUSIBLE' | 'INSUFFICIENT_INFORMATION' | 'POTENTIAL_INCONSISTENCY' | 'CLINICAL_REVIEW_RECOMMENDED';
    summary: string;
    disclaimer: string;
    clinical_review_required: boolean;
    review_reasons: string[];
    guideline_note: string;
    not_assessed_items: string[];
    excluded_administrative_items: string[];
    coverage: 'FULL' | 'PARTIAL' | 'NONE';
  };
  clinical_review: { required: boolean; status: string; human_statement_exists: boolean };
}

export interface ReadinessItem {
  item_id: string;
  label: string;
  status:
    | 'PRESENT'
    | 'MISSING'
    | 'NEEDS_CLINICAL_CONFIRMATION'
    | 'CONFIRMED_BY_REVIEWER'
    | 'REJECTED_BY_REVIEWER'
    | 'REVIEWER_COULD_NOT_DETERMINE';
  evidence_strength: string | null;
  clinical_fact: boolean;
}

export interface ReadinessResponse {
  guidance_label: string;
  items: ReadinessItem[];
  recommended_actions: string[];
  ready_to_submit: boolean;
  disclaimer: string;
  evidence_scope_note: string;
}

export interface TranscriptionTask {
  task_id: string;
  entity_id: string | null;
  field_type: string;
  risk_level: 'HIGH' | 'STANDARD';
  required_reviews: number;
  masked_context: string;
  status: 'OPEN' | 'AWAITING_SECOND_REVIEW' | 'RESOLVED' | 'HUMAN_ESCALATION_REQUIRED' | 'CANCELLED';
  /** RESOLVED only means readers agreed; NOT_APPLIED = the agreed reading could not be placed. */
  outcome?: 'APPLIED' | 'NOT_APPLIED' | null;
  resolution_reason?: string | null;
  final_value: string | null;
  final_value_provenance: Provenance | null;
  readings_received: number;
  assigned_reviewer_count: number;
}
