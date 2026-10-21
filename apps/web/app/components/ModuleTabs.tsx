"use client";

import React from "react";
import { Translations } from "../translations";

export type ModuleTab = "billnyay" | "bimanyay" | "daavisetu" | "schemesetu" | "dawacheck";

const TABS: { id: ModuleTab; icon: string; badge: string }[] = [
  { id: "billnyay", icon: "📊", badge: "CGHS" },
  { id: "daavisetu", icon: "📋", badge: "Pre-Auth" },
  { id: "bimanyay", icon: "🛡️", badge: "IRDAI" },
  { id: "schemesetu", icon: "🏛️", badge: "PMJAY" },
  { id: "dawacheck", icon: "💊", badge: "NPPA" },
];

/** Module tab navigation (mobile touch-friendly scroll). */
export function ModuleTabs({ active, onSelect, t }: { active: ModuleTab; onSelect: (tab: ModuleTab) => void; t: Translations }) {
  return (
    <nav className="module-tabs" role="tablist" aria-label="Feature Modules">
      {TABS.map(({ id, icon, badge }) => (
        <button
          key={id}
          type="button"
          role="tab"
          aria-selected={active === id}
          className={`tab-btn ${active === id ? "active" : ""}`}
          onClick={() => onSelect(id)}
        >
          <span>{icon} {t.tabs[id]}</span>
          <span
            style={{
              fontSize: "0.65rem",
              fontFamily: "var(--font-mono)",
              padding: "0.15rem 0.45rem",
              borderRadius: "var(--radius-full)",
              background: active === id ? "rgba(255, 255, 255, 0.2)" : "var(--bg-surface-elevated)",
              color: active === id ? "#FFFFFF" : "var(--text-muted)",
              border: active === id ? "1px solid rgba(255, 255, 255, 0.3)" : "1px solid var(--border-subtle)"
            }}
          >
            {badge}
          </span>
        </button>
      ))}
    </nav>
  );
}
