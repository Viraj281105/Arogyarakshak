/** SchemeSetu: income profile (#92) and eligibility types. Mirrors the FastAPI schemas in apps/api. */

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
