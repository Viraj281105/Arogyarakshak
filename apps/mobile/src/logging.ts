// Development-only logger: production builds stay silent (no raw console calls in app code).

declare const __DEV__: boolean | undefined;

type Sink = (...args: unknown[]) => void;

export function createDevLogger(isDev: boolean, sink: Sink) {
  return {
    warn: (...args: unknown[]) => {
      if (isDev) sink(...args);
    },
  };
}

const isDev = typeof __DEV__ !== 'undefined' && !!__DEV__;
// eslint-disable-next-line no-console
const devLogger = createDevLogger(isDev, (...a) => console.warn(...a));

export const devWarn = devLogger.warn;
