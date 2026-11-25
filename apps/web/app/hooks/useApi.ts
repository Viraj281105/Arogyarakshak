"use client";

import { useState, useCallback } from "react";

import { msg, type Vars } from "../i18n/format";
import { useT } from "../i18n/useT";
import { API_BASE } from "../lib/apiBase";
import { apiFetch } from "../lib/apiFetch";

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
    return messages.length > 0 ? messages.join("; ") : msg("Request validation failed.");
  }

  if (detail && typeof detail === "object") {
    // The API's own structured refusals carry a readable `message`, sometimes with the
    // fields it could not resolve (e.g. DaaviSetu's 422 `missing_fields`).
    const { message, missing_fields } = detail as { message?: unknown; missing_fields?: unknown };
    if (typeof message === "string" && message.trim()) {
      const missing = Array.isArray(missing_fields)
        ? missing_fields.filter((f): f is string => typeof f === "string").map((f) => f.replace(/_/g, " "))
        : [];
      return missing.length > 0 ? `${message} Missing: ${missing.join(", ")}.` : message;
    }
    // Anything else — summarize instead of exposing arbitrary server-internal shapes.
    try {
      return JSON.stringify(detail);
    } catch {
      return msg("An error occurred.");
    }
  }

  return msg("An error occurred.");
}

/**
 * Shared hook for making API calls with loading/error state management.
 * Prevents duplicate submissions and provides consistent error handling.
 */
export function useApi<T>() {
  const tr = useT();
  // `error` holds an interface string or the server's own text; it is translated on the way out,
  // so changing language also changes a message already on screen.
  const [state, setState] = useState<ApiState<T> & { errorVars?: Vars }>({
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

        const response = await apiFetch(path, fetchOptions);

        if (!response.ok) {
          let errorMessage = msg("API error: HTTP {status}");
          let errorVars: Vars | undefined = { status: response.status };
          try {
            const errorBody = await response.json();
            if (errorBody.detail !== undefined && errorBody.detail !== null) {
              [errorMessage, errorVars] = [normalizeErrorDetail(errorBody.detail), undefined];
            } else if (typeof errorBody.message === "string") {
              [errorMessage, errorVars] = [errorBody.message, undefined];
            }
          } catch {
            // The error body is not JSON: the status line above says what is known.
          }
          setState({ data: null, loading: false, error: errorMessage, errorVars });
          return null;
        }

        const data = (await response.json()) as T;
        setState({ data, loading: false, error: null });
        return data;
      } catch (err) {
        const errorMessage =
          err instanceof Error && err.message.includes("fetch")
            ? msg("Backend server is offline or unreachable. Please ensure the API is running on port 8000.")
            : err instanceof Error
            ? err.message
            : msg("An unexpected error occurred.");

        setState({ data: null, loading: false, error: errorMessage });
        return null;
      }
    },
    []
  );

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  const error = state.error === null ? null : tr(state.error, state.errorVars);
  return { data: state.data, loading: state.loading, error, execute, reset };
}

export { API_BASE };
