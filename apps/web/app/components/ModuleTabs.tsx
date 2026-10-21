"use client";

import React from "react";
import { Translations } from "../translations";

export type ModuleTab = "billnyay" | "bimanyay" | "daavisetu" | "schemesetu" | "dawacheck";

const TABS: { id: ModuleTab; icon: string }[] = [
  { id: "billnyay", icon: "📊" },
  { id: "bimanyay", icon: "🛡️" },
  { id: "daavisetu", icon: "📋" },
  { id: "schemesetu", icon: "🏛️" },
  { id: "dawacheck", icon: "💊" },
];

/** Module tab navigation (mobile touch-friendly scroll). */
export function ModuleTabs({ active, onSelect, t }: { active: ModuleTab; onSelect: (tab: ModuleTab) => void; t: Translations }) {
  return (
    <nav className="module-tabs" role="tablist" aria-label="Feature Modules">
      {TABS.map(({ id, icon }) => (
        <button
          key={id}
          type="button"
          role="tab"
          aria-selected={active === id}
          className={`tab-btn ${active === id ? "active" : ""}`}
          onClick={() => onSelect(id)}
        >
          {icon} {t.tabs[id]}
        </button>
      ))}
    </nav>
  );
}
