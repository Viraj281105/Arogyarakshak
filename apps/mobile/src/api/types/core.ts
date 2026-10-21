/** Case, upload, entity-resolution and error types (Kadi shared layer). Mirrors the FastAPI schemas in apps/api. */

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

export interface ApiError {
  message: string;
  detail?: string;
  statusCode?: number;
}
