/** ADR-011: clinical review, safety governance, readiness and human OCR resolution types. Mirrors the FastAPI schemas in apps/api. */

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
