/** DaaviSetu: pre-authorisation claim types. Mirrors the FastAPI schemas in apps/api. */

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
