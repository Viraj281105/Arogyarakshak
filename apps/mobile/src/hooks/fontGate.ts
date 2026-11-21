// Pure decision for when the app may render after the font load (no react-native import).

/** After this long the app renders with system fonts, so the splash can never hang forever. */
export const FONT_LOAD_TIMEOUT_MS = 6000;

export type FontGateReason = 'pending' | 'loaded' | 'error' | 'timeout';

export function fontGate(state: {
  loaded: boolean;
  error: Error | null | undefined;
  timedOut: boolean;
}): { ready: boolean; reason: FontGateReason } {
  if (state.loaded) return { ready: true, reason: 'loaded' };
  if (state.error != null) return { ready: true, reason: 'error' };
  if (state.timedOut) return { ready: true, reason: 'timeout' };
  return { ready: false, reason: 'pending' };
}
