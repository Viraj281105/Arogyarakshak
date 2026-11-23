"use client";

import React, { useEffect, useId, useRef, useState } from "react";

/**
 * Tooltip for supplementary text only (never the only place information lives). Opens on hover
 * and keyboard focus, closes on Escape (WCAG 1.4.13: dismissible, hoverable, persistent).
 */
export function Tooltip({ content, children }: { content: string; children: React.ReactElement<React.HTMLAttributes<HTMLElement>> }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);
  return (
    <span className="ui-tooltip-wrap" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}>
      {React.cloneElement(children, { "aria-describedby": id })}
      <span role="tooltip" id={id} className="ui-tooltip" data-open={open || undefined}>
        {content}
      </span>
    </span>
  );
}

/** Pure: next tab index for a key (WAI-ARIA tabs, automatic activation). */
export function nextIndexForKey(i: number, count: number, key: string): number | null {
  switch (key) {
    case "ArrowRight":
      return (i + 1) % count;
    case "ArrowLeft":
      return (i - 1 + count) % count;
    case "Home":
      return 0;
    case "End":
      return count - 1;
    default:
      return null;
  }
}

export interface TabItem {
  id: string;
  label: string;
  content: React.ReactNode;
}

/** Tabs (roving tabindex, arrows/Home/End, the selected panel only). Scrolls sideways on phones. */
export function Tabs({ items, label, initial }: { items: readonly TabItem[]; label: string; initial?: string }) {
  const base = useId();
  const [active, setActive] = useState(initial ?? items[0]?.id);
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const current = items.find((t) => t.id === active) ?? items[0];
  if (!current) return null;
  return (
    <div className="ui-tabs">
      <div role="tablist" aria-label={label} className="ui-tablist">
        {items.map((t, i) => (
          <button
            key={t.id}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="tab"
            id={`${base}-tab-${t.id}`}
            aria-selected={t.id === current.id}
            aria-controls={t.id === current.id ? `${base}-panel` : undefined}
            tabIndex={t.id === current.id ? 0 : -1}
            className="ui-tab"
            onClick={() => setActive(t.id)}
            onKeyDown={(e) => {
              const n = nextIndexForKey(i, items.length, e.key);
              if (n === null) return;
              e.preventDefault();
              setActive(items[n].id);
              refs.current[n]?.focus();
            }}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`${base}-panel`} aria-labelledby={`${base}-tab-${current.id}`} tabIndex={0} className="ui-tabpanel">
        {current.content}
      </div>
    </div>
  );
}
