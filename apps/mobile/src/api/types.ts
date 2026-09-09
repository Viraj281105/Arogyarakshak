/**
 * ArogyaRakshak API Request & Response Types
 * Aligned strictly with FastAPI schemas in apps/api/app/api/v1/endpoints/
 */

export interface CaseResponse {
  case_id: string;
  user_id?: string;
  status: string;
  created_at: string;
  extracted_entities?: Record<string, any>;
  raw_text?: string;
}

export interface UploadResponse {
  case_id: string;
  message: string;
  filename: string;
}

export interface BillNyayAuditItem {
  item_name: string;
  charged_amount: number;
  cghs_rate?: number;
  variance?: number;
  flag?: string;
}

export interface BillNyayAuditRequest {
  raw_bill_text?: string;
  items?: BillNyayAuditItem[];
  city_tier?: string;
}

export interface BillNyayAuditResponse {
  case_id?: string;
  total_charged: number;
  total_cghs_benchmark: number;
  potential_savings: number;
  line_items: BillNyayAuditItem[];
  dispute_grounds: string[];
}

export interface DaaviSetuClaimRequest {
  patient_name: string;
  policy_number: string;
  hospital_name: string;
  diagnosis: string;
  estimated_cost: number;
}

export interface DaaviSetuClaimResponse {
  status: string;
  pre_auth_form: Record<string, any>;
  checklist: string[];
  submission_ready: boolean;
}

export interface BimaNyayAnalysisRequest {
  policy_number: string;
  insurer_name: string;
  claimed_amount: number;
  denied_amount: number;
  denial_reason: string;
  diagnosis: string;
  policy_age_years?: number;
}

export interface BimaNyayAnalysisResponse {
  case_id?: string;
  audit_result: {
    status: string;
    grounds: string[];
    statutory_citations: string[];
  };
  appeal_package: {
    level1_gro_appeal: string;
    level2_bima_bharosa: string;
    level3_ombudsman_statement: string;
  };
}

export interface SchemeSetuEligibilityRequest {
  annual_income: number;
  state?: string;
  district?: string;
  ration_card_color?: string;
  diagnosis?: string;
}

export interface SchemeSetuEligibilityResponse {
  eligible_schemes: Array<{
    scheme_name: string;
    coverage_amount: number;
    eligibility_status: string;
    documentation_required: string[];
  }>;
}

export interface DawaCheckBenchmarkRequest {
  medicine_name: string;
  charged_mrp: number;
}

export interface DawaCheckBenchmarkResponse {
  medicine_name: string;
  charged_mrp: number;
  nppa_ceiling_price: number;
  is_overpriced: boolean;
  overcharge_amount: number;
  generic_alternatives: Array<{
    generic_name: string;
    jan_aushadhi_price: number;
    potential_savings: number;
  }>;
}

export interface ApiError {
  message: string;
  detail?: string;
  statusCode?: number;
}
