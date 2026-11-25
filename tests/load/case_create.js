// k6: case creation. PROPOSED, NOT MEASURED (see lib.js). Needs a stack with a raised
// RATE_LIMIT_PER_MINUTE. Run: k6 run tests/load/case_create.js
import { check } from 'k6';
import { SLO, createCase } from './lib.js';

export const options = {
  scenarios: {
    create: {
      executor: 'ramping-arrival-rate',
      startRate: 1,
      timeUnit: '1s',
      preAllocatedVUs: 10,
      maxVUs: 50,
      stages: [
        { target: 5, duration: '30s' },
        { target: 5, duration: '1m' },
      ],
    },
  },
  // proposed, not measured
  thresholds: {
    server_errors: [`rate<${SLO.maxServerErrorRate}`],
    rate_limited: [`rate<${SLO.maxRateLimitedShare}`],
    accepted_requests: ['count>100'],
    iterations: ['count>50'],
    'http_req_duration{name:POST /cases}': [`p(95)<${SLO.createCaseP95Ms}`],
  },
};

export default function () {
  const { res, id } = createCase();
  // A 429 is the rate limiter working, not a failure of this endpoint.
  check(res, { 'created (201) or limited (429)': (r) => r.status === 201 || r.status === 429 });
  if (res.status === 201) {
    check(res, { 'returns a case id': () => Boolean(id) });
  }
}
