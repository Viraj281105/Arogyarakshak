"use client";

import React, { useRef } from "react";
import type { Translations } from "../translations";
import { MODULE_META, MODULE_ORDER, moduleHash, type ModuleTab } from "../shell/nav";
import { MODULE_ICONS } from "../shell/icons/moduleIcons";

export type { ModuleTab };

/** Pure: which tab a key press moves to (WAI-ARIA tabs pattern, automatic activation). */
export function nextTabForKey(current: ModuleTab, key: string, order: readonly ModuleTab[] = MODULE_ORDER): ModuleTab | null {
  const i = order.indexOf(current);
  switch (key) {
    case "ArrowRight":
      return order[(i + 1) % order.length];
    case "ArrowLeft":
      return order[(i - 1 + order.length) % order.length];
    case "Home":
      return order[0];
    case "End":
      return order[order.length - 1];
    default:
      return null;
  }
}

/**
 * The five checks as a tablist (scrolls sideways on phones). Arrow keys/Home/End move between
 * tabs (roving tabindex); the selected check is mirrored into the URL hash (#module-<id>) with
 * replaceState, so the address can be shared and the shell's drawer links land on the same tab.
 */
export function ModuleTabs({ active, onSelect, t }: { active: ModuleTab; onSelect: (tab: ModuleTab) => void; t: Translations }) {
  const refs = useRef<Partial<Record<ModuleTab, HTMLButtonElement | null>>>({});

  const select = (id: ModuleTab, focus = false) => {
    onSelect(id);
    try {
      window.history.replaceState(window.history.state, "", moduleHash(id));
    } catch {
      // The hash is a convenience only.
    }
    if (focus) refs.current[id]?.focus();
  };

  return (
    <div className="module-tabs" role="tablist" aria-label="Feature Modules">
      {MODULE_ORDER.map((id) => {
        const Icon = MODULE_ICONS[id];
        return (
        <button
          key={id}
          ref={(el) => {
            refs.current[id] = el;
          }}
          type="button"
          role="tab"
          id={`tab-${id}`}
          aria-selected={active === id}
          // Only the selected panel is in the DOM, so only its tab points at it.
          aria-controls={active === id ? `panel-${id}` : undefined}
          tabIndex={active === id ? 0 : -1}
          className={`tab-btn ${active === id ? "active" : ""}`}
          onClick={() => select(id)}
          onKeyDown={(e) => {
            const next = nextTabForKey(id, e.key);
            if (!next) return;
            e.preventDefault();
            select(next, true);
          }}
        >
          <Icon size={18} aria-hidden="true" className="site-icon" />
          <span>{t.tabs[id]}</span>
          <span className="tab-badge">{MODULE_META[id].badge}</span>
        </button>
        );
      })}
    </div>
  );
}
