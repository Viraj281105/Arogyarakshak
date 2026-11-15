export interface SmoothScrollInstance {
  destroy(): void;
}
export type SmoothScrollCtor<O> = new (opts: O) => SmoothScrollInstance;

/**
 * Lifecycle for the lazily loaded smooth-scroll library, kept pure so it is testable without a
 * DOM. `load` is the dynamic import (it must stay a literal `import("lenis")` in the caller so
 * the bundler splits it). A rejected load is swallowed: the page keeps native scrolling and
 * nothing is left running. `stop()` is safe at any time, before or after the load settles.
 */
export function startSmoothScroll<O>(
  load: () => Promise<{ default: SmoothScrollCtor<O> }>,
  opts: O,
  onError?: (err: unknown) => void,
): { stop(): void } {
  let cancelled = false;
  let instance: SmoothScrollInstance | undefined;

  load()
    .then(({ default: Ctor }) => {
      if (cancelled) return;
      instance = new Ctor(opts);
    })
    .catch((err: unknown) => {
      instance = undefined;
      try {
        onError?.(err);
      } catch {
        // Reporting must never turn into an unhandled rejection.
      }
    });

  return {
    stop() {
      cancelled = true;
      const current = instance;
      instance = undefined;
      current?.destroy();
    },
  };
}
