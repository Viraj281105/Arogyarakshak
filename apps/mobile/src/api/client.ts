import { ENV } from '../config/env';
import { createClient } from '../shared/api-client';
import { tokenHeaderForPath } from './caseAuth';

/**
 * Robust HTTP client for ArogyaRakshak mobile services
 * Supports timeout, automatic JSON parsing, multipart uploads, and normalized errors.
 */

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

/**
 * Thin adapter over the shared client (packages/api-client, vendored into
 * src/shared/api-client). Timeout, multipart handling, FastAPI error normalisation and
 * the ApiError shape all live there; this file only binds the mobile environment
 * (base URL, timeout) and the ADR-009 case-token header.
 *
 * ADR-009: `tokenHeaderForPath` attaches this case's access token automatically when the
 * endpoint path names a case this session has a token for (and nothing for any other
 * path). An explicit header in `options` (e.g. a deliberate test probing a wrong/foreign
 * token) always wins over the auto-attached one.
 *
 * Every rejection is an ApiError; a network failure or timeout has statusCode 0.
 */
export function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  return createClient({
    baseUrl: ENV.API_BASE_URL,
    timeoutMs: ENV.TIMEOUT_MS,
    headersFor: tokenHeaderForPath,
  }).request<T>(endpoint, options);
}

export const apiClient = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'GET' }),
  post: <T>(endpoint: string, data?: any, options?: RequestOptions) =>
    request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data instanceof FormData ? data : JSON.stringify(data),
    }),
  put: <T>(endpoint: string, data?: any, options?: RequestOptions) =>
    request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data instanceof FormData ? data : JSON.stringify(data),
    }),
  delete: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'DELETE' }),
};
