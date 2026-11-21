// k6: probe endpoints. PROPOSED, NOT MEASURED (see lib.js). Run: k6 run tests/load/health.js
import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, SLO, track } from './lib.js';

export const options = {
  scenarios: {
    probes: {
      executor: 'constant-arrival-rate',
      rate: 20,
      timeUnit: '1s',
      duration: '1m',
      preAllocatedVUs: 10,
      maxVUs: 50,
    },
  },
  // proposed, not measured
  thresholds: {
    server_errors: [`rate<${SLO.maxServerErrorRate}`],
    'http_req_duration{endpoint:live}': [`p(95)<${SLO.healthP95Ms}`],
    'http_req_duration{endpoint:ready}': [`p(95)<${SLO.healthP95Ms}`],
    checks: ['rate>0.99'],
  },
};

export default function () {
  // /health/* is exempt from rate limiting (PROBE_PATHS in app/main.py).
  const live = track(http.get(`${BASE_URL}/health/live`, { tags: { endpoint: 'live' } }));
  const ready = track(http.get(`${BASE_URL}/health/ready`, { tags: { endpoint: 'ready' } }));
  check(live, { 'liveness is 200': (r) => r.status === 200 });
  check(ready, { 'readiness is 200': (r) => r.status === 200 });
}
