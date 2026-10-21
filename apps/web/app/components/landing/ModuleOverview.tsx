"use client";

import React from "react";
import type { ModuleTab } from "../ModuleTabs";
import type { Translations } from "../../translations";

const MODULES: { id: ModuleTab; against: string; icon: React.ReactNode }[] = [
  { id: "billnyay", against: "CGHS 2024 rates", icon: <path d="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6M9 16h3" /> },
  { id: "daavisetu", against: "Insurer pre-authorisation forms", icon: <path d="M8 4h8v3H8zM6 6H5v15h14V6h-1M9 12h6M9 16h4" /> },
  { id: "bimanyay", against: "IRDAI rules & timelines", icon: <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM9 12l2 2 4-4" /> },
  { id: "schemesetu", against: "PM-JAY & MJPJAY eligibility", icon: <path d="M3 10l9-6 9 6M5 10v9M19 10v9M9 10v9M15 10v9M3 21h18" /> },
  { id: "dawacheck", against: "NPPA ceiling prices", icon: <path d="M10.5 4.5a5 5 0 0 1 7 7l-6 6a5 5 0 0 1-7-7zM8 9l7 7" /> },
];

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
            <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
              {m.icon}
            </svg>
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
