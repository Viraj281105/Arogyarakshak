import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  TIMEOUT_MESSAGE,
  canLoadCaseData,
  createRequestGuard,
  initialProcessingState,
  reduceProcessing,
  ProcessingEvent,
  ProcessingState,
} from '../src/services/caseProcessing';
import {
  clearActiveCase,
  getActiveCaseId,
  resolveCaseId,
  setActiveCaseId,
  subscribeActiveCase,
} from '../src/services/activeCase';

const run = (events: ProcessingEvent[], start: ProcessingState = initialProcessingState('CASE-1')) =>
  events.reduce(reduceProcessing, start);

const ev = (status: string, extra: Partial<{ progress: number; log: string; caseId: string }> = {}): ProcessingEvent => ({
  type: 'STREAM_EVENT',
  caseId: extra.caseId ?? 'CASE-1',
  status,
  progress: extra.progress,
  log: extra.log,
});

describe('Case processing lifecycle (demo-hardening pass)', () => {
  it('a screen given a case starts in processing on its first render — no early case read', () => {
    const s = initialProcessingState('CASE-1');
    assert.strictEqual(s.phase, 'processing');
    assert.strictEqual(canLoadCaseData(s), false, 'the old race: case fetched before processing was established');
    assert.strictEqual(initialProcessingState(null).phase, 'idle');
  });

  it('upload 202 -> SSE -> completed -> ready', () => {
    const s = run([ev('upload_received', { progress: 10 }), ev('ocr_start', { progress: 30 }), ev('completed', { log: 'done' })]);
    assert.strictEqual(s.phase, 'ready');
    assert.strictEqual(canLoadCaseData(s), true);
  });

  it('idle (nothing in flight) and duplicate uploads are settled, not processing', () => {
    assert.strictEqual(run([ev('idle')]).phase, 'ready');
    assert.strictEqual(run([ev('duplicate')]).phase, 'ready');
  });

  it('a stream that closes without a terminal event is never treated as completion', () => {
    const s = run([ev('ocr_start'), { type: 'STREAM_CLOSED', caseId: 'CASE-1' }]);
    assert.strictEqual(s.phase, 'processing');
    assert.strictEqual(canLoadCaseData(s), false);
  });

  it('a hung stream times out with the agreed message and does not fake completion', () => {
    const s = run([ev('ocr_start'), { type: 'TIMEOUT', caseId: 'CASE-1' }]);
    assert.strictEqual(s.phase, 'timeout');
    assert.strictEqual(s.message, TIMEOUT_MESSAGE);
    assert.strictEqual(TIMEOUT_MESSAGE, 'Processing is taking longer than expected.');
    assert.strictEqual(canLoadCaseData(s), false);
    assert.strictEqual(run([ev('timeout')]).phase, 'timeout', 'server-side timeout event too');
  });

  it('refreshing after a timeout waits again, and a later completion makes it ready', () => {
    const timedOut = run([{ type: 'TIMEOUT', caseId: 'CASE-1' }]);
    const s = run([{ type: 'REFRESH_STARTED', caseId: 'CASE-1' }, ev('completed')], timedOut);
    assert.strictEqual(s.phase, 'ready');
  });

  it('a timeout after completion does not undo completion', () => {
    const s = run([ev('completed'), { type: 'TIMEOUT', caseId: 'CASE-1' }]);
    assert.strictEqual(s.phase, 'ready');
  });

  it('a late/stale progress event cannot overwrite a completed state', () => {
    const s = run([ev('completed'), ev('ocr_start', { progress: 30 })]);
    assert.strictEqual(s.phase, 'ready');
  });

  it('events for another case are ignored', () => {
    const s = run([ev('completed', { caseId: 'CASE-OTHER' })]);
    assert.strictEqual(s.phase, 'processing');
  });

  it('a failure is reported as failed, never ready', () => {
    const s = run([ev('failed', { log: 'Document processing failed.' })]);
    assert.strictEqual(s.phase, 'failed');
    assert.strictEqual(canLoadCaseData(s), false);
  });

  it('switching case restarts the lifecycle', () => {
    const s = run([ev('completed'), { type: 'CASE_CHANGED', caseId: 'CASE-2' }]);
    assert.deepStrictEqual([s.caseId, s.phase], ['CASE-2', 'processing']);
  });
});

describe('Request guard (stale responses)', () => {
  it('an earlier response is discarded once a newer request began', () => {
    const g = createRequestGuard();
    const first = g.begin();
    const second = g.begin();
    assert.strictEqual(g.isCurrent(first), false);
    assert.strictEqual(g.isCurrent(second), true);
    g.reset();
    assert.strictEqual(g.isCurrent(second), false, 'reset (e.g. processing restarted) drops in-flight answers');
  });
});

describe('Active case shared across tabs', () => {
  it('route caseId wins, otherwise the active case', () => {
    assert.strictEqual(resolveCaseId('CASE-route', 'CASE-active'), 'CASE-route');
    assert.strictEqual(resolveCaseId(undefined, 'CASE-active'), 'CASE-active');
    assert.strictEqual(resolveCaseId(null, null), null);
  });

  it('set / subscribe / clear-only-if-same', () => {
    let calls = 0;
    const unsub = subscribeActiveCase(() => (calls += 1));
    setActiveCaseId('CASE-A');
    assert.strictEqual(getActiveCaseId(), 'CASE-A');
    clearActiveCase('CASE-B');
    assert.strictEqual(getActiveCaseId(), 'CASE-A', 'deleting another case leaves the active one');
    clearActiveCase('CASE-A');
    assert.strictEqual(getActiveCaseId(), null);
    unsub();
    setActiveCaseId('CASE-C');
    assert.strictEqual(calls, 2);
    setActiveCaseId(null);
  });
});

describe('Screens use the lifecycle (source contract)', () => {
  const read = (f: string) => readFileSync(join(__dirname, '..', 'src', f), 'utf-8');

  it('the scan records the active case so DaaviSetu/DawaCheck/BimaNyay receive it', () => {
    assert.ok(/setActiveCaseId\(result\.caseId\)/.test(read('screens/CameraScanScreen.tsx')));
    for (const f of ['BillNyayScreen', 'DaaviSetuScreen', 'BimaNyayScreen', 'DawaCheckScreen']) {
      const src = read(`screens/${f}.tsx`);
      assert.ok(/resolveCaseId\(route\.params\?\.caseId, activeCaseId\)/.test(src), `${f} must fall back to the active case`);
      assert.ok(/<ProcessingStatusCard proc=\{proc\}/.test(src), `${f} must show processing/timeout state`);
    }
  });

  it('BillNyay runs the auto-audit only once extraction is ready', () => {
    const src = read('screens/BillNyayScreen.tsx');
    assert.ok(/pendingAuditFor && proc\.ready/.test(src));
    assert.ok(!/if \(route\.params\.scanCompleted\) \{\s*handleRunAudit/.test(src), 'no audit straight after the 202');
  });

  it('the timeout card offers Refresh status', () => {
    const src = read('components/ProcessingStatusCard.tsx');
    assert.ok(/Processing is taking longer than expected\./.test(src));
    assert.ok(/title="Refresh status"/.test(src));
  });
});
