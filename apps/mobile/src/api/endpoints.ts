import { apiClient } from './client';
import { setCaseAccessToken, clearCaseAccessToken } from './caseAuth';
import {
  CaseResponse,
  CaseCreatedResponse,
  UploadResponse,
  BillNyayAuditResponse,
  BillNyayAppealResponse,
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
  CaseMedicineBenchmark,
  TranslateInstructionsRequest,
  PrescriptionTranslationResponse,
  IncomeProfileRequest,
  IncomeProfileResponse,
  ResolutionDecision,
  ResolutionFeedbackResponse,
  CaseClinicalReview,
  ClinicalReviewRequest,
  ReviewerProfile,
  SafetyEvaluation,
  PlausibilityResponse,
  ReadinessResponse,
  TranscriptionTask,
} from './types';

const enc = encodeURIComponent;

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
    createCase: async (data: { consent_opt_in: boolean; [key: string]: any }) => {
      const created = await apiClient.post<CaseCreatedResponse>('/api/v1/kadi/cases', data);
      // ADR-009: capture the one-time token so client.ts can attach it automatically to
      // every later request for this case_id — see api/caseAuth.ts.
      setCaseAccessToken(created.id, created.access_token);
      return created;
    },

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

    // SEC-03: explicit patient-initiated deletion (P1-10) — the server also purges a
    // case automatically once its retention deadline passes (app/case_retention.py),
    // but the patient does not have to wait for that; this control lets them ask for
    // it now, same as before.
    deleteCase: async (caseId: string) => {
      const result = await apiClient.delete<void>(`/api/v1/kadi/cases/${caseId}`);
      clearCaseAccessToken(caseId);
      return result;
    },

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

    // Runs the 5-agent appeal-drafting pipeline (#18) — persists a signed PDF server
    // side that .../appeal/pdf later serves byte-for-byte (#66).
    appeal: (caseId: string, language: 'en' | 'hi' | 'mr' = 'en') =>
      apiClient.post<BillNyayAppealResponse>(
        `/api/v1/billnyay/cases/${caseId}/appeal?language=${encodeURIComponent(language)}`
      ),

    // ADR-011: bounded plausibility check — never a medical-necessity determination.
    plausibility: (caseId: string) =>
      apiClient.get<PlausibilityResponse>(`/api/v1/billnyay/cases/${enc(caseId)}/clinical-plausibility`),
  },

  // ADR-011 Clinical review (patient side). Every route names the case, so client.ts
  // attaches the case access token automatically.
  clinical: {
    listReviews: (caseId: string, sourceModule?: string) =>
      apiClient.get<CaseClinicalReview[]>(
        `/api/v1/kadi/cases/${enc(caseId)}/clinical-reviews${sourceModule ? `?source_module=${enc(sourceModule)}` : ''}`
      ),
    requestReview: (caseId: string, data: ClinicalReviewRequest) =>
      apiClient.post<CaseClinicalReview>(`/api/v1/kadi/cases/${enc(caseId)}/clinical-reviews`, data),
    assignReviewer: (caseId: string, reviewId: string, reviewerId: string) =>
      apiClient.post<CaseClinicalReview>(
        `/api/v1/kadi/cases/${enc(caseId)}/clinical-reviews/${enc(reviewId)}/assign`,
        { reviewer_id: reviewerId }
      ),
    cancelReview: (caseId: string, reviewId: string) =>
      apiClient.post<CaseClinicalReview>(`/api/v1/kadi/cases/${enc(caseId)}/clinical-reviews/${enc(reviewId)}/cancel`),
    // Lists only independently verified reviewers (or demo fixtures in demo mode). A
    // patient's own doctor is assigned by the reviewer ID they share: reviewerById.
    doctorDirectory: () => apiClient.get<ReviewerProfile[]>('/api/v1/kadi/clinical-reviewers?category=DOCTOR'),
    reviewerById: (reviewerId: string) =>
      apiClient.get<ReviewerProfile>(`/api/v1/kadi/clinical-reviewers/${enc(reviewerId)}`),
    readerDirectory: () => apiClient.get<ReviewerProfile[]>('/api/v1/kadi/clinical-reviewers'),
    safety: (caseId: string) => apiClient.get<SafetyEvaluation>(`/api/v1/kadi/cases/${enc(caseId)}/safety-escalations`),
    transcriptions: (caseId: string) =>
      apiClient.get<TranscriptionTask[]>(`/api/v1/kadi/cases/${enc(caseId)}/transcriptions`),
    flagForTranscription: (caseId: string, entityId: string) =>
      apiClient.post<TranscriptionTask>(`/api/v1/kadi/cases/${enc(caseId)}/transcriptions`, {
        entity_id: entityId,
        field_type: 'MEDICINE_NAME',
      }),
    assignTranscription: (caseId: string, taskId: string, reviewerId: string, shareConsent: boolean) =>
      apiClient.post<TranscriptionTask>(`/api/v1/kadi/cases/${enc(caseId)}/transcriptions/${enc(taskId)}/assign`, {
        reviewer_id: reviewerId,
        share_with_reviewer_consent: shareConsent,
      }),
  },

  // DaaviSetu Cashless Pre-Auth & Claims
  daavisetu: {
    submitClaim: (caseId: string, data: DaaviSetuClaimRequest) =>
      apiClient.post<DaaviSetuClaimResponse>(`/api/v1/daavisetu/cases/${caseId}/claim`, data),

    // ADR-011: documentation completeness — never an approval prediction.
    readiness: (caseId: string) =>
      apiClient.post<ReadinessResponse>(`/api/v1/daavisetu/cases/${enc(caseId)}/readiness`, {}),
    requestClinicalConfirmation: (caseId: string, itemIds: string[], shareConsent: boolean) =>
      apiClient.post<CaseClinicalReview>(`/api/v1/daavisetu/cases/${enc(caseId)}/readiness/clinical-confirmations`, {
        item_ids: itemIds,
        share_with_reviewer_consent: shareConsent,
      }),
  },

  // BimaNyay Insurance Denial & Appeals
  bimanyay: {
    // SEC-04 / ADR-011: when a case is active the dispute record is linked to it. The
    // path contains no "/cases/", so the case token is passed explicitly.
    analyze: (data: BimaNyayAnalysisRequest, language: string = 'en', caseId?: string, caseToken?: string) =>
      apiClient.post<BimaNyayAnalysisResponse>(
        `/api/v1/bimanyay/analyze?language=${encodeURIComponent(language)}${caseId ? `&case_id=${enc(caseId)}` : ''}`,
        data,
        caseId && caseToken ? { headers: { 'X-Case-Access-Token': caseToken } } : undefined
      ),
    clinicalStatements: (caseId: string) =>
      apiClient.get<{ human_clinical_statement_attached: boolean; annex_text: string }>(
        `/api/v1/bimanyay/cases/${enc(caseId)}/clinical-statements`
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
    /** The case's own medicines; unsettled OCR readings come back NOT benchmarked. */
    caseBenchmark: (caseId: string) =>
      apiClient.get<CaseMedicineBenchmark[]>(`/api/v1/dawacheck/cases/${encodeURIComponent(caseId)}/benchmark`),
  },
};
