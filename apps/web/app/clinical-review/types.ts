import type { ClinicalStatement, FactDecision } from "../lib/clinical";

// The reviewer never holds the patient's case id (the server omits it).
export interface AssignedReview {
  review_id: string;
  source_module: string;
  review_type: "CLINICAL_STATEMENT" | "FACT_CONFIRMATION";
  status: string;
  clinical_question: string;
  trigger?: string;
  evidence_scope?: string[];
  insurer_name?: string | null;
  created_at?: string;
  assigned_at?: string | null;
  accepted_at?: string | null;
  coi_context: { hospital_names: string[]; insurer_name: string | null; note: string };
  coi_label: string | null;
  coi_disclosure?: string | null;
}

export interface ReviewerDetail extends AssignedReview {
  statements: ClinicalStatement[];
  facts: FactDecision[];
  finalization_confirmation_text: string;
  fact_decision_confirmation_text: string;
}

export interface TranscriptionView {
  task_id: string;
  field_type: string;
  risk_level: string;
  masked_context: string;
  location_hint?: { segment_index?: number | null; bbox?: number[][] | null } | null;
  ocr_candidate: string | null;
  ocr_candidate_hidden: boolean;
  accepting_readings: boolean;
  your_reading: { value: string | null; unreadable: boolean } | null;
  instructions: string;
}

export interface RuleView {
  rule_id: string;
  rule_key: string;
  version: number;
  title: string;
  status: string;
  description: string;
  trigger: { match_any: string[]; context_types: string[] };
  action: { type: string; severity: string; message: string };
  source: { name: string; reference: string | null; version: string | null; section: string | null };
  limitations: string;
  proposed_by: { name: string; reviewer_id: string; verification_label: string } | null;
  approvals: { decision: string; comment: string | null; reviewer: { name: string; verification_label: string }; applies_to_current_content: boolean }[];
  review_due_date: string;
  review_overdue: boolean;
  is_demo: boolean;
  retirement_requested_by?: string | null;
}

export type Tab = "reviews" | "transcriptions" | "safety";

/** Runs an action, clearing and then setting the page-level error/notice banners. */
export type Guard = (fn: () => Promise<void>, ok?: string) => Promise<void>;

/** A reviewer-authenticated API call (the credential is bound by the page). */
export type ReviewerCall = <T = unknown>(path: string, method?: "GET" | "POST" | "PUT", body?: unknown) => Promise<T>;

export const MODULE_LABEL: Record<string, string> = {
  billnyay: "BillNyay — hospital bill audit",
  bimanyay: "BimaNyay — insurance denial appeal",
  daavisetu: "DaaviSetu — pre-authorization readiness",
  dawacheck: "DawaCheck — medicines",
  kadi: "Case context",
};

// Mirrors kadi.clinical_review.types.ReviewTrigger.
export const TRIGGER_LABEL: Record<string, string> = {
  MANUAL: "The patient asked for a clinical review",
  PLAUSIBILITY_FLAG: "The software's plausibility check flagged something it cannot judge",
  DENIAL_CATEGORY: "The insurer's denial turns on clinical judgment",
  SAFETY_RULE: "A clinical safety rule fired",
  READINESS_CLINICAL_FACT: "The pre-authorization relies on clinical facts only a doctor can confirm",
};

export interface StatementEditorState {
  statementId: string;
  selected: string[];
  text: string;
  limitations: string;
}

export type FactInput = Record<string, { decision: string; note: string; confirm: boolean }>;
