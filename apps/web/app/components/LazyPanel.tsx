import React from "react";

/**
 * Placeholder shown while a code-split (next/dynamic) panel's chunk loads. Sized close to the real
 * panel so its arrival does not push content around, and announced as busy to assistive tech.
 * No hooks: safe as a next/dynamic `loading` component.
 */
export function LazyPanel({ minHeight, label = "Loading…" }: { minHeight: string; label?: string }) {
  return (
    <div className="lazy-panel" role="status" aria-busy="true" style={{ minHeight }}>
      <span className="spinner" aria-hidden="true" />
      <span className="sr-only">{label}</span>
    </div>
  );
}
