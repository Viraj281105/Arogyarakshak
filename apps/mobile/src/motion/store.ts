import { AccessibilityInfo } from 'react-native';
import { createReducedMotionStore } from './logic';

/** App-level singleton; App.tsx primes it while the splash screen is up. */
export const reducedMotionStore = createReducedMotionStore(AccessibilityInfo);
