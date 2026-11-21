// k6: document upload (accept path only: 202). PROPOSED, NOT MEASURED (see lib.js).
// Run: k6 run tests/load/upload.js
import http from 'k6/http';
import { check } from 'k6';
import { API, SLO, authHeaders, createCase, syntheticBill, track } from './lib.js';

export const options = {
  scenarios: {
    upload: {
      executor: 'constant-arrival-rate',
      rate: 2,
      timeUnit: '1s',
      duration: '1m',
      preAllocatedVUs: 10,
      maxVUs: 40,
    },
  },
  // proposed, not measured
  thresholds: {
    server_errors: [`rate<${SLO.maxServerErrorRate}`],
    'http_req_duration{name:POST /upload}': [`p(95)<${SLO.uploadAcceptP95Ms}`],
  },
};

export default function () {
  const { id, token } = createCase();
  if (!id) {
    return; // rate limited or create failed; already counted by createCase
  }
  const bill = http.file(syntheticBill(__ITER), 'bill.txt', 'text/plain');
  const res = track(
    http.post(
      `${API}/cases/${id}/upload`,
      { file: bill },
      { headers: authHeaders(token), tags: { name: 'POST /upload' } },
    ),
  );
  check(res, { 'accepted (202) or limited (429)': (r) => r.status === 202 || r.status === 429 });
}
