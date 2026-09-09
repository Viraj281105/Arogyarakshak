import { ENV } from '../config/env';
import { ApiError } from './types';

/**
 * Robust HTTP client for ArogyaRakshak mobile services
 * Supports timeout, automatic JSON parsing, multipart uploads, and normalized errors.
 */

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

export async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const url = `${ENV.API_BASE_URL}${endpoint}`;
  const timeoutMs = options.timeoutMs ?? ENV.TIMEOUT_MS;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const headers: Record<string, string> = {
    Accept: 'application/json',
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
        errorDetail = errorJson.detail || errorJson.message || JSON.stringify(errorJson);
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
