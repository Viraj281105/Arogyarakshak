// Shared helpers for the k6 load scripts (WS3 / Wave 2 stream E).
//
// STATUS: PROPOSED, NOT MEASURED. Nothing in this directory has been executed against a
// running stack; k6 was not available when it was written. The thresholds below are
// targets taken from the SLO table in docs/operations/observability.md (themselves
// "proposed for a demo deployment; not measured results"). Do not quote a latency or
// throughput figure from these scripts until a run's own k6 summary says so.
//
// Rate limiting: the API limits each client IP to RATE_LIMIT_PER_MINUTE requests
// (default 120, app/rate_limit.py) and k6 presents one IP. Run against a throw-away
// stack started with a raised limit (docs/operations/load-and-chaos.md), never against a
// shared or production deployment. 429s are counted separately and are NOT server errors.
import http from 'k6/http';
import { Rate, Counter } from 'k6/metrics';

export const BASE_URL = (__ENV.BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');
export const API = `${BASE_URL}/api/v1/kadi`;

// SLO "Availability: 99.5 % of requests not 5xx" (observability.md) -> at most 0.5 % 5xx.
export const serverErrors = new Rate('server_errors');
export const rateLimited = new Counter('rate_limited_responses');
// Share of responses that were 429, and a count of 2xx responses. Without thresholds on these a
// run against the default 120 requests/minute limit would "pass" while almost every request was
// rejected early and nothing was measured.
export const rateLimitedShare = new Rate('rate_limited');
export const accepted = new Counter('accepted_requests');

export const SLO = {
  // proposed, not measured: derived from the availability SLO above.
  maxServerErrorRate: 0.005,
  // proposed, not measured: more than this share of 429s means the rate limiter, not the API, was measured.
  maxRateLimitedShare: 0.05,
  // proposed, not measured: "95 % of documents processed within 10 s" (TARGET_LATENCY_SECONDS).
  caseProcessingP95Ms: 10000,
  // proposed, not measured: NO request-latency SLO exists in observability.md. These are
  // engineering placeholders for cheap endpoints; replace once a baseline run exists.
  healthP95Ms: 500,
  createCaseP95Ms: 1000,
  uploadAcceptP95Ms: 2000,
};

// Records the outcome of one response against the availability SLI.
export function track(res) {
  serverErrors.add(res.status >= 500);
  rateLimitedShare.add(res.status === 429);
  if (res.status === 429) {
    rateLimited.add(1);
  }
  if (res.status >= 200 && res.status < 300) {
    accepted.add(1);
  }
  return res;
}

const JSON_HEADERS = { 'Content-Type': 'application/json' };

// Every API call needs an account session (ADR-029). Each virtual user signs in once, with a
// throwaway account unless LOAD_EMAIL and LOAD_PASSWORD name one. Raise AUTH_RATE_LIMIT_PER_MINUTE
// on the throw-away stack too, or the sign-ins themselves are limited.
let bearer = null;

function signIn() {
  const email = __ENV.LOAD_EMAIL || `load-${__VU}-${Date.now()}@example.org`;
  const password = __ENV.LOAD_PASSWORD || `${Math.random().toString(36).slice(2)}${Date.now()}`;
  const params = { headers: JSON_HEADERS, tags: { name: 'sign-in' } };
  if (!__ENV.LOAD_EMAIL) {
    http.post(`${API}/auth/register`, JSON.stringify({ email, password }), params);
  }
  const res = http.post(
    `${API}/auth/login`,
    JSON.stringify({ email, password, session_transport: 'bearer' }),
    params,
  );
  return res.status === 200 ? res.json().token : null;
}

export function authHeaders() {
  if (!bearer) {
    bearer = signIn();
  }
  return bearer ? { Authorization: `Bearer ${bearer}` } : {};
}

// Creates a case and returns { res, id }; id is null on 429 or failure. Synthetic data only.
export function createCase(tags) {
  const res = track(
    http.post(`${API}/cases`, JSON.stringify({ consent_opt_in: false }), {
      headers: Object.assign({}, JSON_HEADERS, authHeaders()),
      tags: Object.assign({ name: 'POST /cases' }, tags || {}),
    }),
  );
  if (res.status !== 201) {
    return { res, id: null };
  }
  const body = res.json();
  return { res, id: body.id };
}

// A tiny synthetic hospital bill (no real person, no real hospital). Each call varies the
// text so the per-case duplicate-document guard does not short-circuit the pipeline.
export function syntheticBill(seed) {
  return [
    'Synthetic Test Hospital',
    'Diagnosis: K35.8 Acute appendicitis',
    `Consultation ${500 + (seed % 50)}`,
    'X-Ray Chest 400',
    'Laparoscopic Appendectomy 45000',
    `Total: ${45900 + (seed % 50)}`,
    '',
  ].join('\n');
}
