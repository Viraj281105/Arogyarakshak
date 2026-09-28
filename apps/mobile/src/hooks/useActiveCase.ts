import { useSyncExternalStore } from 'react';
import { getActiveCaseId, subscribeActiveCase } from '../services/activeCase';

/** The patient's active case (set by the scan flow), shared across module tabs. */
export function useActiveCaseId(): string | null {
  return useSyncExternalStore(subscribeActiveCase, getActiveCaseId, getActiveCaseId);
}
