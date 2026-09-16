import { ENV } from '../config/env';
import { ApiError } from './types';
import { tokenHeaderForPath } from './caseAuth';

/**
 * Robust HTTP client for ArogyaRakshak mobile services
 * Supports timeout, automatic JSON parsing, multipart uploads, and normalized errors.
 */

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

/**
 * Normalizes a FastAPI error body's `detail` into a plain string. `detail` is a plain
 * string for most handled errors, but FastAPI's automatic 422 validation responses send
 * an ARRAY of {loc, msg, type} objects — passing that through as `ApiError.detail`
 * (typed `string`) would hand callers a non-string at runtime, and any screen
 * interpolating it directly (`${apiErr.detail}`) would render "[object Object]" instead
 * of a readable message.
 */
function normalizeErrorDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      if (item && typeof item === 'object' && 'msg' in item) {
        const loc = Array.isArray((item as any).loc)
          ? (item as any).loc.filter((p: unknown) => p !== 'body').join('.')
          : undefined;
        return loc ? `${loc}: ${(item as any).msg}` : String((item as any).msg);
      }
      return typeof item === 'string' ? item : JSON.stringify(item);
    });
    return messages.join('; ') || 'Request validation failed.';
  }
  if (detail && typeof detail === 'object') {
    try {
      return JSON.stringify(detail);
    } catch {
      return 'An error occurred.';
    }
  }
  return 'An error occurred.';
}

export async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const url = `${ENV.API_BASE_URL}${endpoint}`;
  const timeoutMs = options.timeoutMs ?? ENV.TIMEOUT_MS;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  // ADR-009: attaches this case's access token automatically when the endpoint path
  // names a case this session has a token for. An explicit header in `options` (e.g. a
  // deliberate test probing a wrong/foreign token) always wins over the auto-attached one.
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...tokenHeaderForPath(endpoint),
    ...(options.headers as Record<string, string>),
  };

  // If body is not FormData, set Content-Type to application/json by default
  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorDetail: string | undefined;
      try {
        const errorJson = await response.json();
        errorDetail =
          errorJson.detail !== undefined && errorJson.detail !== null
            ? normalizeErrorDetail(errorJson.detail)
            : typeof errorJson.message === 'string'
            ? errorJson.message
            : JSON.stringify(errorJson);
      } catch {
        errorDetail = await response.text();
      }

      const error: ApiError = {
        message: `HTTP Error ${response.status}: ${response.statusText}`,
        detail: errorDetail,
        statusCode: response.status,
      };
      throw error;
    }

    // A 204 No Content (e.g. DELETE /cases/{id}) has no body — calling .json() on it
    // throws a parse error despite the request having succeeded.
    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      const timeoutError: ApiError = {
        message: `Request timed out after ${timeoutMs}ms`,
        statusCode: 408,
      };
      throw timeoutError;
    }
    if (err.statusCode) {
      throw err;
    }
    const genericError: ApiError = {
      message: err.message || 'Network request failed',
    };
    throw genericError;
  }
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
