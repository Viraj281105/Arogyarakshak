/**
 * Clinical review client helpers (ADR-011).
 *
 * Wording rules every clinical surface follows:
 * - a reviewer's verification is shown ONLY via the server's `verification_label`
 *   (never "Verified Doctor" composed on the client);
 * - every human output shows its provenance and conflict of interest;
 * - nothing machine-derived is ever styled as a clinician's opinion.
 *
 * Copy is English-first. Hindi/Marathi versions of these medico-legal strings are pending
 * native-speaker review and are deliberately not machine-drafted here.
 */

import { API_BASE, caseAuthHeaders, normalizeErrorDetail } from "../hooks/useApi";

export type Provenance = "AI_DERIVED" | "HUMAN_REVIEWED" | "HUMAN_AUTHORED" | "EXTERNAL_SOURCE" | "PATIENT_PROVIDED";

export const PROVENANCE_LABELS: Record<Provenance, string> = {
  AI_DERIVED: "Machine-derived",
  HUMAN_REVIEWED: "Human-reviewed",
  HUMAN_AUTHORED: "Human-authored",
  EXTERNAL_SOURCE: "External source",
  PATIENT_PROVIDED: "Patient-provided",
};

export const COI_OPTIONS: { value: string; label: string }[] = [
  { value: "INDEPENDENT_REVIEWER", label: "Independent — no relationship with patient, hospital or insurer" },
  { value: "TREATING_DOCTOR", label: "I am the treating doctor" },
  { value: "HOSPITAL_AFFILIATED", label: "Affiliated with the treating hospital" },
  { value: "INSURER_AFFILIATED", label: "Affiliated with the insurer" },
  { value: "OTHER", label: "Other relationship (disclosure required)" },
];

export const SAFETY_FLOOR_DISCLAIMER =
  "This safety layer is a decision-support floor, not a substitute for professional clinical assessment.";

export interface ReviewerProfile {
  id: string;
  name: string;
  designation: string | null;
  category: string;
  category_label: string;
  specialty: string | null;
  registration_number: string | null;
  registration_authority: string | null;
  verification_status: "UNVERIFIED" | "SELF_DECLARED" | "DEMO_VERIFIED" | "EXTERNALLY_VERIFIED";
  verification_label: string;
  affiliation: string | null;
  is_safety_board_member?: boolean;
}

export interface ReviewerSnapshot extends Omit<ReviewerProfile, "id"> {
  reviewer_id: string;
}

export interface EvidenceItem {
  item_id: string;
  kind: string;
  label: string;
  value?: string;
  provenance: Provenance;
  source: string;
}

export interface ClinicalStatement {
  statement_id: string;
  review_id: string;
  statement_version: number;
  supersedes_statement_id: string | null;
  status: "DRAFT" | "UNDER_REVIEW" | "FINALIZED" | "SUPERSEDED" | "WITHDRAWN";
  provenance: Provenance;
  clinical_question: string;
  evidence_reviewed: EvidenceItem[];
  reviewer_statement: string;
  limitations: string;
  coi_category: string;
  coi_label: string | null;
  coi_disclosure: string | null;
  reviewer_snapshot: ReviewerSnapshot | null;
  reviewer_confirmation: boolean;
  finalized_at: string | null;
  content_sha256: string | null;
  withdrawn_reason: string | null;
}

export interface FactDecision {
  fact_id: string;
  fact_key: string;
  fact_question: string;
  decision: "PENDING" | "CONFIRMED" | "REJECTED" | "CANNOT_DETERMINE";
  provenance: Provenance | null;
  reviewer_note: string | null;
  reviewer_snapshot: ReviewerSnapshot | null;
  coi_label: string | null;
  decided_at: string | null;
}

export interface CaseClinicalReview {
  review_id: string;
  source_module: string;
  review_type: "CLINICAL_STATEMENT" | "FACT_CONFIRMATION";
  status: "REQUESTED" | "ASSIGNED" | "IN_REVIEW" | "COMPLETED" | "DECLINED" | "CANCELLED";
  clinical_question: string;
  trigger: string;
  assigned_reviewer: ReviewerProfile | null;
  coi_label: string | null;
  coi_disclosure: string | null;
  evidence_shared: EvidenceItem[];
  human_statement_exists: boolean;
  current_statement: ClinicalStatement | null;
  statement_history: ClinicalStatement[];
  draft_in_progress: boolean;
  facts: FactDecision[];
  created_at: string;
}

export interface AuditEvent {
  id: string;
  event_type: string;
  actor_type: string;
  actor_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface SafetyEscalation {
  rule_id: string;
  rule_key: string;
  rule_version: number;
  title: string;
  severity: "URGENT" | "ADVISORY";
  message: string;
  matched_terms: string[];
  source: { name: string; version: string | null; section: string | null };
  limitations: string[];
  rule_review_overdue: boolean;
  human_review_recommended: boolean;
  disclaimer: string;
}

export interface SafetyEvaluation {
  case_id: string;
  active_rule_count: number;
  escalations: SafetyEscalation[];
  disclaimer: string;
  coverage_note: string;
  scope_note?: string;
}

export interface TranscriptionTask {
  task_id: string;
  entity_id: string | null;
  source: string;
  field_type: string;
  risk_level: "HIGH" | "STANDARD";
  required_reviews: number;
  ocr_candidate: string | null;
  masked_context: string;
  status: "OPEN" | "AWAITING_SECOND_REVIEW" | "RESOLVED" | "HUMAN_ESCALATION_REQUIRED" | "CANCELLED";
  resolution_reason: string | null;
  final_value: string | null;
  final_value_provenance: Provenance | null;
  readings_received: number;
  assigned_reviewer_count: number;
  readings: { value: string | null; unreadable: boolean; reviewer_name: string | null; reviewer_role: string | null }[];
}

const K = "/api/v1/kadi";

export const clinicalPaths = {
  reviewers: () => `${K}/clinical-reviewers`,
  reviewerMe: () => `${K}/clinical-reviewers/me`,
  caseReviews: (caseId: string, module?: string) =>
    `${K}/cases/${encodeURIComponent(caseId)}/clinical-reviews${module ? `?source_module=${encodeURIComponent(module)}` : ""}`,
  caseReview: (caseId: string, reviewId: string) =>
    `${K}/cases/${encodeURIComponent(caseId)}/clinical-reviews/${encodeURIComponent(reviewId)}`,
  assign: (caseId: string, reviewId: string) => `${clinicalPaths.caseReview(caseId, reviewId)}/assign`,
  cancel: (caseId: string, reviewId: string) => `${clinicalPaths.caseReview(caseId, reviewId)}/cancel`,
  caseAudit: (caseId: string, reviewId: string) => `${clinicalPaths.caseReview(caseId, reviewId)}/audit`,
  safety: (caseId: string) => `${K}/cases/${encodeURIComponent(caseId)}/safety-escalations`,
  transcriptions: (caseId: string) => `${K}/cases/${encodeURIComponent(caseId)}/transcriptions`,
  assignTranscription: (caseId: string, taskId: string) =>
    `${K}/cases/${encodeURIComponent(caseId)}/transcriptions/${encodeURIComponent(taskId)}/assign`,
  plausibility: (caseId: string) => `/api/v1/billnyay/cases/${encodeURIComponent(caseId)}/clinical-plausibility`,
  readiness: (caseId: string) => `/api/v1/daavisetu/cases/${encodeURIComponent(caseId)}/readiness`,
  factConfirmation: (caseId: string) => `/api/v1/daavisetu/cases/${encodeURIComponent(caseId)}/readiness/clinical-confirmations`,
  // Reviewer-side (X-Reviewer-Token)
  assigned: () => `${K}/clinical-reviews/assigned`,
  reviewerReview: (reviewId: string) => `${K}/clinical-reviews/${encodeURIComponent(reviewId)}`,
  accept: (reviewId: string) => `${clinicalPaths.reviewerReview(reviewId)}/accept`,
  decline: (reviewId: string) => `${clinicalPaths.reviewerReview(reviewId)}/decline`,
  evidence: (reviewId: string) => `${clinicalPaths.reviewerReview(reviewId)}/evidence`,
  statements: (reviewId: string) => `${clinicalPaths.reviewerReview(reviewId)}/statements`,
  statement: (reviewId: string, statementId: string) =>
    `${clinicalPaths.statements(reviewId)}/${encodeURIComponent(statementId)}`,
  factDecision: (reviewId: string, factId: string) =>
    `${clinicalPaths.reviewerReview(reviewId)}/facts/${encodeURIComponent(factId)}/decision`,
  reviewerAudit: (reviewId: string) => `${clinicalPaths.reviewerReview(reviewId)}/audit`,
  myTranscriptions: () => `${K}/transcriptions/assigned`,
  transcriptionReadings: (taskId: string) => `${K}/transcriptions/${encodeURIComponent(taskId)}/readings`,
  safetyRules: () => `${K}/safety-rules`,
  safetyWorkspace: () => `${K}/safety-rules/workspace`,
  safetyRule: (ruleId: string) => `${K}/safety-rules/${encodeURIComponent(ruleId)}`,
};

export function reviewerHeaders(token: string | undefined | null): Record<string, string> {
  return token ? { "X-Reviewer-Token": token } : {};
}

/** Only these statuses may be shown to a patient as a clinician's current opinion. */
export function isCurrentOpinion(statement: Pick<ClinicalStatement, "status"> | null | undefined): boolean {
  return statement?.status === "FINALIZED";
}

export async function clinicalRequest<T>(
  path: string,
  options: { method?: "GET" | "POST" | "PUT"; body?: unknown; caseToken?: string; reviewerToken?: string } = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      ...caseAuthHeaders(options.caseToken),
      ...reviewerHeaders(options.reviewerToken),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail !== undefined) message = normalizeErrorDetail(body.detail);
    } catch {
      // keep the status message
    }
    throw new Error(message);
  }
  return (await res.json()) as T;
}
