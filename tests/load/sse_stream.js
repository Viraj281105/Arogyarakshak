// k6: upload, then follow the SSE progress stream to its terminal event and record the
// end-to-end time. PROPOSED, NOT MEASURED (see lib.js). Run: k6 run tests/load/sse_stream.js
//
// k6's http client buffers the whole response, which is acceptable here because the API
// closes the stream after a `completed` or `failed` event (or its own timeout event).
// Stay well below the stack's single-process capacity (ADR-019: exactly one API process).
import http from 'k6/http';
import { check } from 'k6';
import { Trend } from 'k6/metrics';
import { API, SLO, authHeaders, createCase, syntheticBill, track } from './lib.js';

const caseProcessing = new Trend('case_processing_ms', true);

export const options = {
  scenarios: {
    stream: { executor: 'constant-vus', vus: 5, duration: '2m' },
  },
  // proposed, not measured: SLO "95 % of documents processed within 10 s".
  thresholds: {
    server_errors: [`rate<${SLO.maxServerErrorRate}`],
    rate_limited: [`rate<${SLO.maxRateLimitedShare}`],
    accepted_requests: ['count>20'],
    iterations: ['count>10'],
    case_processing_ms: [`p(95)<${SLO.caseProcessingP95Ms}`],
    checks: ['rate>0.95'],
  },
};

function terminalStatus(body) {
  const events = body
    .split('\n')
    .filter((l) => l.startsWith('data: '))
    .map((l) => JSON.parse(l.slice(6)));
  return events.length ? events[events.length - 1].status : null;
}

export default function () {
  const { id } = createCase();
  if (!id) {
    return;
  }
  const started = Date.now();
  const bill = http.file(syntheticBill(__ITER * 7 + __VU), 'bill.txt', 'text/plain');
  const up = track(
    http.post(
      `${API}/cases/${id}/upload`,
      { file: bill },
      { headers: authHeaders(), tags: { name: 'POST /upload' } },
    ),
  );
  if (up.status !== 202) {
    return;
  }
  const stream = track(
    http.get(`${API}/cases/${id}/stream`, {
      headers: authHeaders(),
      timeout: '60s',
      tags: { name: 'GET /stream' },
    }),
  );
  const status = stream.status === 200 ? terminalStatus(stream.body) : null;
  caseProcessing.add(Date.now() - started);
  check(stream, { 'stream ends in completed': () => status === 'completed' });
}
