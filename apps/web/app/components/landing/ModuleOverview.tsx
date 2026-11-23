"use client";

import React from "react";
import type { ModuleTab } from "../ModuleTabs";
import type { Translations } from "../../translations";
import { MODULE_ICONS } from "../../shell/icons/moduleIcons";

const MODULES: { id: ModuleTab; against: string }[] = [
  { id: "billnyay", against: "CGHS 2024 rates" },
  { id: "daavisetu", against: "Insurer pre-authorisation forms" },
  { id: "bimanyay", against: "IRDAI rules & timelines" },
  { id: "schemesetu", against: "PM-JAY & MJPJAY eligibility" },
  { id: "dawacheck", against: "NPPA ceiling prices" },
];

function ModuleIcon({ id }: { id: ModuleTab }) {
  const Icon = MODULE_ICONS[id];
  return <Icon size={22} aria-hidden="true" className="lp-icon" />;
}

/** The five checks, each opening its real module tab below. */
export const ModuleOverview: React.FC<{ t: Translations; onOpen: (tab: ModuleTab) => void }> = ({ t, onOpen }) => (
  <section className="lp-section lp-modules" aria-labelledby="lp-modules-title">
    <header className="lp-section-head" data-reveal>
      <p className="lp-kicker">Five checks, one case</p>
      <h2 id="lp-modules-title" className="lp-heading">Upload once. Every check reads the same case.</h2>
    </header>
    <ul className="lp-module-grid">
      {MODULES.map((m, i) => (
        <li key={m.id} className="lp-module-card" data-reveal style={{ "--i": i } as React.CSSProperties}>
          <span className="lp-module-icon">
            <ModuleIcon id={m.id} />
          </span>
          <h3>{t.tabs[m.id]}</h3>
          <span className="lp-module-against">Compared with {m.against}</span>
          <p>{t.modules[m.id].desc}</p>
          <button type="button" className="lp-module-open" onClick={() => onOpen(m.id)} aria-label={`Open ${t.tabs[m.id]}`}>
            Open module
            <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </button>
        </li>
      ))}
    </ul>
  </section>
);
