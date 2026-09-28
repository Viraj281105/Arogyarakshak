/**
 * Case processing lifecycle (patient mobile flow).
 *
 *   scan -> upload 202 -> processing -> SSE -> extraction complete -> case ready
 *
 * Pure, React-free logic so it can be unit-tested under plain Node (tests/*.test.ts):
 *
 * - A screen that receives a caseId starts in `processing` on its FIRST render. Previously
 *   "processing" was derived from `isStreaming`, which is false until the stream effect
 *   runs, so screens fetched the case once before extraction had even started.
 * - `ready` only comes from a server event (`completed`, or `idle` = nothing in flight
 *   for this case) or an explicit status refresh — never from the absence of events.
 * - A hung stream becomes `timeout` ("Processing is taking longer than expected"); it is
 *   never promoted to `ready`. The patient can refresh the status.
 * - Responses are sequence-guarded, so an early/stale response cannot overwrite a newer one.
 */

export type ProcessingPhase = 'idle' | 'processing' | 'ready' | 'failed' | 'timeout';

export interface ProcessingState {
  caseId: string | null;
  phase: ProcessingPhase;
  /** Last server log line, shown to the patient (already user-facing text). */
  message: string | null;
  progress: number;
}

export type ProcessingEvent =
  | { type: 'CASE_CHANGED'; caseId: string | null }
  | { type: 'STREAM_EVENT'; caseId: string; status: string; progress?: number; log?: string }
  | { type: 'STREAM_CLOSED'; caseId: string }
  | { type: 'TIMEOUT'; caseId: string }
  | { type: 'REFRESH_STARTED'; caseId: string };

/** Default client-side ceiling for a silent/hung stream. */
export const PROCESSING_TIMEOUT_MS = 90_000;

export const TIMEOUT_MESSAGE = 'Processing is taking longer than expected.';

export function initialProcessingState(caseId: string | null): ProcessingState {
  return { caseId, phase: caseId ? 'processing' : 'idle', message: null, progress: 0 };
}

const READY_STATUSES = new Set(['completed', 'idle', 'duplicate']);

export function reduceProcessing(state: ProcessingState, event: ProcessingEvent): ProcessingState {
  if (event.type === 'CASE_CHANGED') {
    return event.caseId === state.caseId ? state : initialProcessingState(event.caseId);
  }
  // Events for a case this screen no longer shows are stale.
  if (event.caseId !== state.caseId) return state;

  switch (event.type) {
    case 'REFRESH_STARTED':
      return { ...state, phase: 'processing', message: null };
    case 'TIMEOUT':
      // Only a still-running wait can time out; a finished one stays finished.
      return state.phase === 'processing' ? { ...state, phase: 'timeout', message: TIMEOUT_MESSAGE } : state;
    case 'STREAM_CLOSED':
      // A stream that closes without a terminal event proves nothing: keep waiting (the
      // timeout, or a refresh, resolves it). Never assume completion.
      return state;
    case 'STREAM_EVENT': {
      const progress = typeof event.progress === 'number' ? event.progress : state.progress;
      const message = event.log ?? state.message;
      if (READY_STATUSES.has(event.status)) return { ...state, phase: 'ready', progress: 100, message };
      if (event.status === 'failed') return { ...state, phase: 'failed', progress, message };
      if (event.status === 'timeout') return { ...state, phase: 'timeout', progress, message: TIMEOUT_MESSAGE };
      // A late progress event must not reopen a case that already finished.
      if (state.phase === 'ready' || state.phase === 'failed') return state;
      return { ...state, phase: 'processing', progress, message };
    }
    default:
      return state;
  }
}

/** Case-derived data may be loaded only once processing has settled successfully. */
export function canLoadCaseData(state: ProcessingState): boolean {
  return state.caseId !== null && state.phase === 'ready';
}

/**
 * Sequence guard for async loads: `begin()` returns a token; `isCurrent(token)` is false
 * once a newer load has begun or the guard was reset, so a slow earlier response can be
 * discarded instead of overwriting fresher state.
 */
export function createRequestGuard() {
  let latest = 0;
  return {
    begin(): number {
      latest += 1;
      return latest;
    },
    isCurrent(token: number): boolean {
      return token === latest;
    },
    reset(): void {
      latest += 1;
    },
  };
}
