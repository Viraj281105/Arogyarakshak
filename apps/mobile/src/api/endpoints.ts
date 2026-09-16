import { apiClient } from './client';
import {
  CaseResponse,
  UploadResponse,
  BillNyayAuditResponse,
  DaaviSetuClaimRequest,
  DaaviSetuClaimResponse,
  BimaNyayAnalysisRequest,
  BimaNyayAnalysisResponse,
  BimaNyayTimelineRequest,
  BimaNyayTimelineResponse,
  SchemeSetuEligibilityRequest,
  SchemeResult,
  DawaCheckBenchmarkRequest,
  DawaCheckBenchmarkResponse,
  TranslateInstructionsRequest,
  PrescriptionTranslationResponse,
  IncomeProfileRequest,
  IncomeProfileResponse,
  ResolutionDecision,
  ResolutionFeedbackResponse,
} from './types';

/**
 * Domain Endpoint Mapping for ArogyaRakshak API Gateway
 * Routes aligned with apps/api/app/api/v1/endpoints/
 */

export const api = {
  // Shared Kadi Context Layer
  kadi: {
    // consent_opt_in is REQUIRED and never defaulted. The backend enforces the stored
    // value, so silently sending `true` here would have granted consent on the
    // patient's behalf without them ever being asked.
    createCase: (data: { consent_opt_in: boolean; [key: string]: any }) =>
      apiClient.post<CaseResponse>('/api/v1/kadi/cases', data),

    uploadDocument: async (
      caseId: string,
      fileBlobOrUri: Blob | { uri: string; name: string; type: string }
    ) => {
      const formData = new FormData();
      if ('uri' in fileBlobOrUri) {
        formData.append('file', fileBlobOrUri as any);
      } else {
        formData.append('file', fileBlobOrUri);
      }
      return apiClient.post<UploadResponse>(`/api/v1/kadi/cases/${caseId}/upload`, formData);
    },

    getCase: (caseId: string) =>
      apiClient.get<{ case: CaseResponse; entities: any[] }>(`/api/v1/kadi/cases/${caseId}`),

    // "Are these the same?" questions Kadi could not decide on its own (#31).
    getPendingResolutions: (caseId: string) =>
      apiClient.get<ResolutionDecision[]>(
        `/api/v1/kadi/cases/${encodeURIComponent(caseId)}/resolutions?status=pending`
      ),

    submitResolutionFeedback: (caseId: string, decisionId: string, sameEntity: boolean) =>
      apiClient.post<ResolutionFeedbackResponse>(
        `/api/v1/kadi/cases/${encodeURIComponent(caseId)}/resolutions/${encodeURIComponent(decisionId)}/feedback`,
        { same_entity: sameEntity }
      ),
  },

  // BillNyay Hospital Bill Audit
  billnyay: {
    audit: (caseId: string) =>
      apiClient.post<BillNyayAuditResponse>(`/api/v1/billnyay/cases/${caseId}/audit`),
  },

  // DaaviSetu Cashless Pre-Auth & Claims
  daavisetu: {
    submitClaim: (caseId: string, data: DaaviSetuClaimRequest) =>
      apiClient.post<DaaviSetuClaimResponse>(`/api/v1/daavisetu/cases/${caseId}/claim`, data),
  },

  // BimaNyay Insurance Denial & Appeals
  bimanyay: {
    analyze: (data: BimaNyayAnalysisRequest, language: string = 'en') =>
      apiClient.post<BimaNyayAnalysisResponse>(
        `/api/v1/bimanyay/analyze?language=${encodeURIComponent(language)}`,
        data
      ),
    getTimeline: (data: BimaNyayTimelineRequest) =>
      apiClient.post<BimaNyayTimelineResponse>('/api/v1/bimanyay/timeline', data),
  },

  // SchemeSetu Welfare Eligibility
  schemesetu: {
    checkEligibility: (data: SchemeSetuEligibilityRequest) =>
      apiClient.post<SchemeResult[]>('/api/v1/schemesetu/eligibility', data),

    // Consent-bounded: the API refuses (403) unless the case was created with consent (#92).
    saveIncomeProfile: (caseId: string, data: IncomeProfileRequest) =>
      apiClient.put<IncomeProfileResponse>(
        `/api/v1/schemesetu/cases/${encodeURIComponent(caseId)}/income-profile`,
        data
      ),
  },

  // DawaCheck Medicine MRP & Generics
  dawacheck: {
    benchmark: (data: DawaCheckBenchmarkRequest) =>
      apiClient.post<DawaCheckBenchmarkResponse>('/api/v1/dawacheck/benchmark', data),
    translateInstructions: (data: TranslateInstructionsRequest) =>
      apiClient.post<PrescriptionTranslationResponse>('/api/v1/dawacheck/translate-instructions', data),
  },
};
