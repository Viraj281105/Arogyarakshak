import { useState, useEffect, useRef, useCallback } from 'react';
import { ENV } from '../config/env';
import { noteUnauthorized, sessionHeaders } from '../api/session';
import { tr } from '../translations/tr';

export interface SSEStreamEvent {
  status: 'upload_received' | 'ocr_start' | 'extraction_start' | 'database_write' | 'completed' | 'failed' | string;
  progress: number;
  log: string;
  step?: number;
  timestamp?: number;
}

export interface UseSSEStreamResult {
  events: SSEStreamEvent[];
  latestEvent: SSEStreamEvent | null;
  progress: number;
  isStreaming: boolean;
  isCompleted: boolean;
  isFailed: boolean;
  error: string | null;
  startStream: (caseId: string) => void;
  stopStream: () => void;
  resetStream: () => void;
}

export function useSSEStream(initialCaseId?: string): UseSSEStreamResult {
  const [events, setEvents] = useState<SSEStreamEvent[]>([]);
  const [latestEvent, setLatestEvent] = useState<SSEStreamEvent | null>(null);
  const [progress, setProgress] = useState(0);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const [isFailed, setIsFailed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const stopStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const resetStream = useCallback(() => {
    stopStream();
    setEvents([]);
    setLatestEvent(null);
    setProgress(0);
    setIsCompleted(false);
    setIsFailed(false);
    setError(null);
  }, [stopStream]);

  const handleMessagePayload = useCallback((payloadText: string) => {
    try {
      const data: SSEStreamEvent = JSON.parse(payloadText);
      setEvents((prev) => [...prev, data]);
      setLatestEvent(data);
      if (typeof data.progress === 'number') {
        setProgress(data.progress);
      }
      // 'idle' = nothing is being processed for this case (the server says so);
      // 'duplicate' = already ingested. Both mean the case is settled.
      if (data.status === 'completed' || data.status === 'idle' || data.status === 'duplicate') {
        setIsCompleted(true);
        setIsStreaming(false);
      } else if (data.status === 'timeout') {
        // The server stopped waiting; this is NOT completion.
        setIsStreaming(false);
      } else if (data.status === 'failed') {
        setIsFailed(true);
        setIsStreaming(false);
        setError(data.log || tr('Processing failed'));
      }
    } catch (e) {
      console.warn('[useSSEStream] Failed to parse SSE event payload:', e);
    }
  }, []);

  const startStream = useCallback((caseId: string) => {
    resetStream();
    if (!caseId) return;

    setIsStreaming(true);
    const streamPath = `/api/v1/kadi/cases/${caseId}/stream`;
    const streamUrl = `${ENV.API_BASE_URL}${streamPath}`;
    // EventSource cannot send headers and a session never goes in a URL, so the stream is read
    // with fetch, with the session in the Authorization header (ADR-029).
    const controller = new AbortController();
    abortControllerRef.current = controller;

    (async () => {
      try {
        const response = await fetch(streamUrl, {
          signal: controller.signal,
          headers: {
            Accept: 'text/event-stream',
            ...sessionHeaders(),
          },
        });

        if (response.status === 401) noteUnauthorized(streamPath);
        if (!response.ok) {
          throw new Error(tr('HTTP {status}: Failed to connect to event stream', { status: response.status }));
        }

        // If body has getReader (fetch streaming)
        if (response.body && typeof (response.body as any).getReader === 'function') {
          const reader = (response.body as any).getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split('\n\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
              const trimmed = line.trim();
              if (trimmed.startsWith('data:')) {
                const dataPart = trimmed.slice(5).trim();
                handleMessagePayload(dataPart);
              }
            }
          }
        } else {
          // Fallback: Read full text when stream closes
          const fullText = await response.text();
          const lines = fullText.split('\n\n');
          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('data:')) {
              handleMessagePayload(trimmed.slice(5).trim());
            }
          }
        }
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          console.warn('[useSSEStream] Stream error:', err);
          setError(err.message || tr('Stream connection error'));
        }
      } finally {
        setIsStreaming(false);
      }
    })();
  }, [handleMessagePayload, resetStream]);

  useEffect(() => {
    if (initialCaseId) {
      startStream(initialCaseId);
    }
    return () => {
      stopStream();
    };
  }, [initialCaseId, startStream, stopStream]);

  return {
    events,
    latestEvent,
    progress,
    isStreaming,
    isCompleted,
    isFailed,
    error,
    startStream,
    stopStream,
    resetStream,
  };
}
