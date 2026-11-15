import { useSyncExternalStore } from 'react';
import { isReduced } from './logic';
import { reducedMotionStore } from './store';

const getSnapshot = () => reducedMotionStore.get();

/**
 * OS reduce-motion preference, read synchronously from the primed store. Until the preference is
 * known this returns true (final state), so reduced-motion users never see an animation start.
 */
export function useReducedMotion(): boolean {
  return isReduced(useSyncExternalStore(reducedMotionStore.subscribe, getSnapshot, getSnapshot));
}
