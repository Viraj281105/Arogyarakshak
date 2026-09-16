"use client";

import { useState, useCallback } from "react";

const API_BASE =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    : "http://localhost:8000";

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

/**
 * ADR-009: builds the header carrying a case's access token. Every case-scoped request
 * needs this; omitted (empty object) when no token is available yet, so a caller can
 * spread it unconditionally: `headers: { ...caseAuthHeaders(caseToken) }`.
 */
export function caseAuthHeaders(caseToken: string | undefined | null): Record<string, string> {
  return caseToken ? { "X-Case-Access-Token": caseToken } : {};
}

/**
 * Normalizes a FastAPI error body's `detail` into a plain, renderable string.
 *
 * `detail` is a plain string for most handled errors (404/403/etc.), but FastAPI's
 * automatic 422 validation responses send an ARRAY of {loc, msg, type} objects, and a
 * handler can in principle send any JSON-serializable value. Rendering `detail`
 * directly as `{error}` in JSX crashes React ("Objects are not valid as a React
 * child") the first time a 422 or a structured detail reaches the UI — never assume
 * it is already a string.
 */
export function normalizeErrorDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          const loc = Array.isArray((item as { loc?: unknown[] }).loc)
            ? (item as { loc: unknown[] }).loc.filter((p) => p !== "body").join(".")
            : undefined;
          const msg = String((item as { msg: unknown }).msg);
          return loc ? `${loc}: ${msg}` : msg;
        }
        return typeof item === "string" ? item : JSON.stringify(item);
      })
      .filter(Boolean);
    return messages.length > 0 ? messages.join("; ") : "Request validation failed.";
  }

  if (detail && typeof detail === "object") {
    // A structured (non-array) detail — never render it raw; summarize instead of
    // exposing arbitrary server-internal object shapes to the UI.
    try {
      return JSON.stringify(detail);
    } catch {
      return "An error occurred.";
    }
  }

  return "An error occurred.";
}

/**
 * Shared hook for making API calls with loading/error state management.
 * Prevents duplicate submissions and provides consistent error handling.
 */
export function useApi<T>() {
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = useCallback(
    async (
      path: string,
      options: {
        method?: "GET" | "POST" | "PUT" | "DELETE";
        body?: unknown;
        headers?: Record<string, string>;
      } = {}
    ): Promise<T | null> => {
      // Prevent duplicate submissions
      setState((prev) => {
        if (prev.loading) return prev;
        return { data: null, loading: true, error: null };
      });

      try {
        const { method = "POST", body, headers = {} } = options;

        const fetchOptions: RequestInit = {
          method,
          headers: {
            "Content-Type": "application/json",
            ...headers,
          },
        };

        if (body !== undefined) {
          fetchOptions.body = JSON.stringify(body);
        }

        const response = await fetch(`${API_BASE}${path}`, fetchOptions);

        if (!response.ok) {
          let errorMessage = `API error: HTTP ${response.status}`;
          try {
            const errorBody = await response.json();
            if (errorBody.detail !== undefined && errorBody.detail !== null) {
              errorMessage = normalizeErrorDetail(errorBody.detail);
            } else if (typeof errorBody.message === "string") {
              errorMessage = errorBody.message;
            }
          } catch {
            // If error body is not JSON, use status text
            errorMessage = `API error: ${response.status} ${response.statusText}`;
          }
          setState({ data: null, loading: false, error: errorMessage });
          return null;
        }

        const data = (await response.json()) as T;
        setState({ data, loading: false, error: null });
        return data;
      } catch (err) {
        const errorMessage =
          err instanceof Error && err.message.includes("fetch")
            ? "Backend server is offline or unreachable. Please ensure the API is running on port 8000."
            : err instanceof Error
            ? err.message
            : "An unexpected error occurred.";

        setState({ data: null, loading: false, error: errorMessage });
        return null;
      }
    },
    []
  );

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  return { ...state, execute, reset };
}

export { API_BASE };
