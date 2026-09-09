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
} from './types';

/**
 * Domain Endpoint Mapping for ArogyaRakshak API Gateway
 * Routes aligned with apps/api/app/api/v1/endpoints/
 */

export const api = {
  // Shared Kadi Context Layer
  kadi: {
    createCase: (data?: { consent_opt_in?: boolean; user_id?: string; [key: string]: any }) =>
      apiClient.post<CaseResponse>('/api/v1/kadi/cases', { consent_opt_in: true, ...data }),

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
  },

  // DawaCheck Medicine MRP & Generics
  dawacheck: {
    benchmark: (data: DawaCheckBenchmarkRequest) =>
      apiClient.post<DawaCheckBenchmarkResponse>('/api/v1/dawacheck/benchmark', data),
  },
};
