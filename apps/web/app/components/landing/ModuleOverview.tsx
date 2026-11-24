"use client";

import React, { useId, useRef, useState } from "react";

/**
 * The landing page's interactive six-capability overview (Wave 3 M3): a vertical tablist with a
 * roving tabindex (arrow keys, Home/End) and one panel per capability. Tab labels and panels are
 * rendered on the server (LandingSections.tsx) and passed in as nodes, so the copy, icons and
 * badges add no client JS; this component only decides which panel is visible.
 */
export function ModuleOverview({
  ids,
  labels,
  panels,
  label,
}: {
  ids: readonly string[];
  labels: readonly React.ReactNode[];
  panels: readonly React.ReactNode[];
  label: string;
}) {
  const [active, setActive] = useState(0);
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const base = useId();

  const focusTab = (i: number) => {
    const next = (i + ids.length) % ids.length;
    setActive(next);
    tabs.current[next]?.focus();
  };

  const onKeyDown = (e: React.KeyboardEvent, i: number) => {
    const keys: Record<string, number> = {
      ArrowDown: i + 1,
      ArrowRight: i + 1,
      ArrowUp: i - 1,
      ArrowLeft: i - 1,
      Home: 0,
      End: ids.length - 1,
    };
    if (!(e.key in keys)) return;
    e.preventDefault();
    focusTab(keys[e.key]);
  };

  return (
    <div className="pub-cap">
      <div className="pub-cap-tabs" role="tablist" aria-label={label} aria-orientation="vertical">
        {ids.map((id, i) => (
          <button
            key={id}
            ref={(el) => {
              tabs.current[i] = el;
            }}
            type="button"
            role="tab"
            id={`${base}-tab-${id}`}
            aria-selected={active === i}
            aria-controls={`${base}-panel-${id}`}
            tabIndex={active === i ? 0 : -1}
            className="pub-cap-tab"
            data-module={id}
            onClick={() => setActive(i)}
            onKeyDown={(e) => onKeyDown(e, i)}
          >
            {labels[i]}
          </button>
        ))}
      </div>
      {ids.map((id, i) => (
        <div
          key={id}
          role="tabpanel"
          id={`${base}-panel-${id}`}
          aria-labelledby={`${base}-tab-${id}`}
          hidden={active !== i}
          tabIndex={0}
          className="pub-cap-panel"
          data-module={id}
        >
          {panels[i]}
        </div>
      ))}
    </div>
  );
}
