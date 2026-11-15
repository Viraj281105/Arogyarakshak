import { isApiError, makeApiError, normalizeErrorDetail } from "./errors";

export interface ClientOptions {
  baseUrl: string;
  /** Default request timeout. */
  timeoutMs?: number;
  /** Injected for tests; defaults to the global `fetch`, resolved at request time. */
  fetchImpl?: typeof fetch;
  /** Extra headers for a request path (e.g. a per-case access token). Called with exactly the request path. */
  headersFor?: (path: string) => Record<string, string>;
}

export type RequestOptions = RequestInit & { timeoutMs?: number };

const DEFAULT_TIMEOUT_MS = 30000;

function headersToRecord(h: RequestInit["headers"]): Record<string, string> {
  const out: Record<string, string> = {};
  if (!h) return out;
  if (Array.isArray(h)) {
    for (const [k, v] of h) out[k] = v;
  } else if (typeof (h as Headers).forEach === "function" && typeof (h as Headers).get === "function") {
    (h as unknown as { forEach(cb: (value: string, key: string) => void): void }).forEach((v, k) => {
      out[k] = v;
    });
  } else {
    Object.assign(out, h as Record<string, string>);
  }
  return out;
}

const hasHeader = (headers: Record<string, string>, name: string) =>
  Object.keys(headers).some((k) => k.toLowerCase() === name);

const isFormData = (body: unknown) => typeof FormData !== "undefined" && body instanceof FormData;

async function errorDetailOf(response: Response): Promise<string> {
  let text = "";
  try {
    text = await response.text();
  } catch {
    return response.statusText || "An error occurred.";
  }
  try {
    const body = JSON.parse(text) as Record<string, unknown> | null;
    if (body && typeof body === "object") {
      if (body.detail !== undefined && body.detail !== null) return normalizeErrorDetail(body.detail);
      return typeof body.message === "string" ? body.message : JSON.stringify(body);
    }
  } catch {
    // not JSON: fall through to the raw text
  }
  return text || response.statusText || "An error occurred.";
}

/**
 * Plain-TypeScript HTTP client (no React, no React Native, no Node-only APIs): timeout via
 * AbortController, JSON bodies get a JSON content-type (FormData does not), FastAPI error
 * details are normalized, and EVERY rejection is an `ApiError` (network failure and timeout
 * are status 0, never a raw TypeError/AbortError).
 */
export function createClient(o: ClientOptions): { request<T>(path: string, init?: RequestOptions): Promise<T> } {
  const base = o.baseUrl.replace(/\/+$/, "");

  async function request<T>(path: string, init: RequestOptions = {}): Promise<T> {
    const { timeoutMs: perRequestTimeout, ...fetchInit } = init;
    const timeoutMs = perRequestTimeout ?? o.timeoutMs ?? DEFAULT_TIMEOUT_MS;

    // The explicit headers passed to this call always win over the auto-attached ones.
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...(o.headersFor ? o.headersFor(path) : {}),
      ...headersToRecord(fetchInit.headers),
    };
    if (fetchInit.body && !isFormData(fetchInit.body) && !hasHeader(headers, "content-type")) {
      headers["Content-Type"] = "application/json";
    }

    const controller = new AbortController();
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);
    const callerSignal = fetchInit.signal;
    const onCallerAbort = () => controller.abort();
    if (callerSignal) {
      if (callerSignal.aborted) controller.abort();
      else callerSignal.addEventListener("abort", onCallerAbort);
    }

    try {
      const doFetch = o.fetchImpl ?? fetch;
      const response = await doFetch(`${base}${path}`, { ...fetchInit, headers, signal: controller.signal });

      if (!response.ok) {
        throw makeApiError(
          response.status,
          `HTTP Error ${response.status}: ${response.statusText}`,
          await errorDetailOf(response),
        );
      }
      // A 204 No Content has no body; calling .json() on it would throw despite success.
      if (response.status === 204) return undefined as T;
      try {
        return (await response.json()) as T;
      } catch {
        throw makeApiError(response.status, "The server returned an unreadable response.");
      }
    } catch (err: unknown) {
      if (isApiError(err)) throw err;
      const name = (err as { name?: string } | null)?.name;
      if (name === "AbortError" || controller.signal.aborted) {
        throw makeApiError(0, timedOut ? `Request timed out after ${timeoutMs}ms` : "Request was aborted");
      }
      const message = (err as { message?: unknown } | null)?.message;
      throw makeApiError(0, typeof message === "string" && message ? message : "Network request failed");
    } finally {
      clearTimeout(timer);
      callerSignal?.removeEventListener("abort", onCallerAbort);
    }
  }

  return { request };
}
