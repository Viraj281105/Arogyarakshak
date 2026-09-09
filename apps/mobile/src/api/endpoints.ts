import { apiClient } from './client';
import {
  CaseResponse,
  UploadResponse,
  BillNyayAuditRequest,
  BillNyayAuditResponse,
  DaaviSetuClaimRequest,
  DaaviSetuClaimResponse,
  BimaNyayAnalysisRequest,
  BimaNyayAnalysisResponse,
  SchemeSetuEligibilityRequest,
  SchemeSetuEligibilityResponse,
  DawaCheckBenchmarkRequest,
  DawaCheckBenchmarkResponse,
} from './types';

/**
 * Domain Endpoint Mapping for ArogyaRakshak API Gateway
 */

export const api = {
  // Shared Kadi Context Layer
  kadi: {
    createCase: (data?: { user_id?: string; raw_text?: string }) =>
      apiClient.post<CaseResponse>('/api/v1/kadi/cases', data),

    uploadDocument: async (
      caseId: string,
      fileBlobOrUri: Blob | { uri: string; name: string; type: string }
    ) => {
      const formData = new FormData();
      formData.append('case_id', caseId);

      if ('uri' in fileBlobOrUri) {
        // React Native specific file representation
        formData.append('file', fileBlobOrUri as any);
      } else {
        formData.append('file', fileBlobOrUri);
      }

      return apiClient.post<UploadResponse>('/api/v1/kadi/upload', formData);
    },

    getCase: (caseId: string) =>
      apiClient.get<CaseResponse>(`/api/v1/kadi/cases/${caseId}`),
  },

  // BillNyay Hospital Bill Audit
  billnyay: {
    audit: (data: BillNyayAuditRequest) =>
      apiClient.post<BillNyayAuditResponse>('/api/v1/billnyay/audit', data),
  },

  // DaaviSetu Cashless Pre-Auth & Claims
  daavisetu: {
    submitClaim: (data: DaaviSetuClaimRequest) =>
      apiClient.post<DaaviSetuClaimResponse>('/api/v1/daavisetu/claim', data),
  },

  // BimaNyay Insurance Denial & Appeals
  bimanyay: {
    analyze: (data: BimaNyayAnalysisRequest, language: string = 'en') =>
      apiClient.post<BimaNyayAnalysisResponse>(
        `/api/v1/bimanyay/analyze?language=${encodeURIComponent(language)}`,
        data
      ),
    getTimeline: (caseId: string) =>
      apiClient.get<any>(`/api/v1/bimanyay/timeline/${caseId}`),
  },

  // SchemeSetu Welfare Eligibility
  schemesetu: {
    checkEligibility: (data: SchemeSetuEligibilityRequest) =>
      apiClient.post<SchemeSetuEligibilityResponse>('/api/v1/schemesetu/eligibility', data),
  },

  // DawaCheck Medicine MRP & Generics
  dawacheck: {
    benchmark: (data: DawaCheckBenchmarkRequest) =>
      apiClient.post<DawaCheckBenchmarkResponse>('/api/v1/dawacheck/benchmark', data),
  },
};
