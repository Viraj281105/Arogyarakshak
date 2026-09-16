import { useState, useEffect, useCallback, useRef } from 'react';
import { useOfflineStorage } from './useOfflineStorage';
import { useNetworkStatus } from './useNetworkStatus';
import { api } from '../api';
import { hydrateCaseAccessTokens } from '../api/caseAuth';

export interface QueuedAction {
  id: string;
  type: 'BENCHMARK_MEDICINE' | 'CHECK_SCHEME' | 'SUBMIT_PREAUTH' | 'ANALYZE_DENIAL' | string;
  payload: any;
  timestamp: number;
  retryCount: number;
  // SEC-14: set when the last replay attempt failed with 401/403 (missing/invalid case
  // access token) — kept in the queue rather than retry-counted toward deletion, since a
  // missing credential will not fix itself by retrying the same request again.
  needsReauth?: boolean;
}

const QUEUE_STORAGE_KEY = 'offline_action_queue';
const MAX_RETRIES = 3;

export function useOfflineQueue() {
  const { getItem, setItem } = useOfflineStorage();
  const { isOnline } = useNetworkStatus();
  const [queue, setQueue] = useState<QueuedAction[]>([]);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const isProcessingRef = useRef<boolean>(false);

  // Load queue on initial mount. SEC-14: case access tokens are re-hydrated from
  // secure storage FIRST and awaited before the queue is populated — otherwise
  // setQueue([...]) below could make queue.length > 0 and fire the auto-flush effect
  // (processQueue) while the in-memory token Map is still empty post-restart, replaying
  // every action with no token attached at all.
  useEffect(() => {
    (async () => {
      try {
        await hydrateCaseAccessTokens();
      } catch (e) {
        console.warn('[useOfflineQueue] Failed to hydrate case access tokens:', e);
      }
      try {
        const stored = await getItem(QUEUE_STORAGE_KEY);
        if (stored) {
          const parsed = JSON.parse(stored);
          if (Array.isArray(parsed)) {
            setQueue(parsed);
          }
        }
      } catch (e) {
        console.warn('[useOfflineQueue] Failed to load offline queue:', e);
      }
    })();
  }, [getItem]);

  // Persist queue updates to storage. Returns whether the write actually succeeded —
  // P2: useOfflineStorage.setItem's 50,000-CHARACTER guard does not reflect
  // expo-secure-store's real on-device limit (Android's Keystore-backed store caps
  // entries around ~2,048 BYTES), so a queue serialization between those two sizes can
  // pass the app-level guard and still fail the actual platform write. setItem already
  // catches that and returns false; this hook previously never looked at the return
  // value, so a failed persist looked identical to a successful one to every caller.
  const saveQueue = useCallback(
    async (newQueue: QueuedAction[]): Promise<boolean> => {
      setQueue(newQueue);
      try {
        return await setItem(QUEUE_STORAGE_KEY, JSON.stringify(newQueue));
      } catch (e) {
        console.warn('[useOfflineQueue] Failed to persist offline queue:', e);
        return false;
      }
    },
    [setItem]
  );

  // Enqueue action when network is offline or request fails. Returns null — instead of
  // silently returning an id as if the action were safely queued — when the underlying
  // persist failed, so a caller can tell the user their action was NOT actually saved
  // for offline retry rather than showing a false "queued" confirmation.
  const enqueueAction = useCallback(
    async (type: string, payload: any): Promise<string | null> => {
      const id = `act_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
      const newAction: QueuedAction = {
        id,
        type,
        payload,
        timestamp: Date.now(),
        retryCount: 0,
      };

      const updated = [...queue, newAction];
      const saved = await saveQueue(updated);
      return saved ? id : null;
    },
    [queue, saveQueue]
  );

  // Remove specific action from queue
  const dequeueAction = useCallback(
    async (id: string) => {
      const updated = queue.filter((item) => item.id !== id);
      await saveQueue(updated);
    },
    [queue, saveQueue]
  );

  // Clear all pending actions
  const clearQueue = useCallback(async () => {
    await saveQueue([]);
  }, [saveQueue]);

  // Process/replay pending actions against backend API
  const processQueue = useCallback(async (): Promise<{
    processed: number;
    failed: number;
    needsReauth: number;
  }> => {
    if (isProcessingRef.current || queue.length === 0) {
      return { processed: 0, failed: 0, needsReauth: 0 };
    }

    isProcessingRef.current = true;
    setIsProcessing(true);

    let processedCount = 0;
    let failedCount = 0;
    let needsReauthCount = 0;
    const remainingActions: QueuedAction[] = [];

    for (const action of queue) {
      try {
        switch (action.type) {
          case 'BENCHMARK_MEDICINE':
            await api.dawacheck.benchmark(action.payload);
            break;
          case 'CHECK_SCHEME':
            await api.schemesetu.checkEligibility(action.payload);
            break;
          case 'SUBMIT_PREAUTH':
            if (action.payload.caseId) {
              await api.daavisetu.submitClaim(action.payload.caseId, action.payload.claimData);
            }
            break;
          case 'ANALYZE_DENIAL':
            await api.bimanyay.analyze(action.payload.data, action.payload.language);
            break;
          default:
            console.warn(`[useOfflineQueue] Unrecognized action type: ${action.type}`);
        }
        processedCount++;
      } catch (err) {
        console.warn(`[useOfflineQueue] Failed to replay action ${action.id}:`, err);
        // SEC-14: a 401/403 means this case's access token is missing or no longer
        // valid (e.g. the case expired/was purged server-side — see app/case_retention)
        // — replaying the SAME action again will deterministically fail again, so
        // burning it down through MAX_RETRIES like an ordinary transient failure would
        // just silently discard it once retries run out ("permanently jamming" it by
        // dropping it without ever telling anyone). Instead it is kept in the queue
        // indefinitely (not retry-counted) so it can still succeed if the token comes
        // back (e.g. the case is re-scanned, re-issuing a token this session), and other
        // queued actions are not blocked from processing either way.
        const statusCode = (err as { statusCode?: number } | null)?.statusCode;
        if (statusCode === 401 || statusCode === 403) {
          needsReauthCount++;
          remainingActions.push({ ...action, needsReauth: true });
        } else if (action.retryCount + 1 < MAX_RETRIES) {
          remainingActions.push({ ...action, retryCount: action.retryCount + 1 });
        } else {
          failedCount++;
        }
      }
    }

    await saveQueue(remainingActions);
    isProcessingRef.current = false;
    setIsProcessing(false);

    return { processed: processedCount, failed: failedCount, needsReauth: needsReauthCount };
  }, [queue, saveQueue]);

  // Automatically flush queue when device transitions from offline to online
  useEffect(() => {
    if (isOnline && queue.length > 0 && !isProcessingRef.current) {
      processQueue();
    }
  }, [isOnline, queue.length, processQueue]);

  return {
    queue,
    queueLength: queue.length,
    isProcessing,
    enqueueAction,
    dequeueAction,
    clearQueue,
    processQueue,
  };
}
