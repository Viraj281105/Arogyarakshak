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
            if (errorBody.detail) {
              errorMessage = errorBody.detail;
            } else if (errorBody.message) {
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
