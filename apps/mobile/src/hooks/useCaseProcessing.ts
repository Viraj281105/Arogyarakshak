import { useCallback, useEffect, useReducer, useRef } from 'react';
import { useSSEStream } from './useSSEStream';
import {
  PROCESSING_TIMEOUT_MS,
  ProcessingState,
  canLoadCaseData,
  initialProcessingState,
  reduceProcessing,
} from '../services/caseProcessing';

export interface CaseProcessing extends ProcessingState {
  /** Case-derived data (entities, benchmarks, readiness) may be loaded now. */
  ready: boolean;
  processing: boolean;
  timedOut: boolean;
  failed: boolean;
  /** Re-reads the processing status from the server (replays or reports idle). */
  refreshStatus: () => void;
  sse: ReturnType<typeof useSSEStream>;
}

/**
 * Processing lifecycle for the case a screen shows. See services/caseProcessing for the
 * rules; in short: `processing` from the first render, `ready` only on a server event,
 * `timeout` after PROCESSING_TIMEOUT_MS without any event, never a faked completion.
 */
export function useCaseProcessing(caseId: string | null, timeoutMs: number = PROCESSING_TIMEOUT_MS): CaseProcessing {
  const sse = useSSEStream(caseId ?? undefined);
  const [stored, dispatch] = useReducer(reduceProcessing, caseId, initialProcessingState);
  // Derived synchronously so the very first render for a new case is already `processing`.
  const state = stored.caseId === caseId ? stored : initialProcessingState(caseId);

  useEffect(() => {
    dispatch({ type: 'CASE_CHANGED', caseId });
  }, [caseId]);

  const consumed = useRef(0);
  useEffect(() => {
    if (!caseId) return;
    if (sse.events.length < consumed.current) consumed.current = 0; // stream restarted
    for (const ev of sse.events.slice(consumed.current)) {
      dispatch({ type: 'STREAM_EVENT', caseId, status: ev.status, progress: ev.progress, log: ev.log });
    }
    consumed.current = sse.events.length;
  }, [caseId, sse.events]);

  // Inactivity timeout: restarted by every event, active only while still processing.
  useEffect(() => {
    if (!caseId || state.phase !== 'processing') return;
    const timer = setTimeout(() => dispatch({ type: 'TIMEOUT', caseId }), timeoutMs);
    return () => clearTimeout(timer);
  }, [caseId, state.phase, sse.events.length, timeoutMs]);

  const { startStream } = sse;
  const refreshStatus = useCallback(() => {
    if (!caseId) return;
    consumed.current = 0;
    dispatch({ type: 'REFRESH_STARTED', caseId });
    startStream(caseId);
  }, [caseId, startStream]);

  return {
    ...state,
    ready: canLoadCaseData(state),
    processing: state.phase === 'processing',
    timedOut: state.phase === 'timeout',
    failed: state.phase === 'failed',
    refreshStatus,
    sse,
  };
}
