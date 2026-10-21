"use client";

import React, { useEffect, useState } from "react";
import { DemoStatus, fetchDemoStatus, simulatedTone } from "../../lib/demo";
import { TONE_CLASS } from "../../lib/labels";

/** Reads the server's demo status once. `null` until known (or if the API is unreachable). */
export function useDemoStatus(): DemoStatus | null {
  const [status, setStatus] = useState<DemoStatus | null>(null);
  useEffect(() => {
    let cancelled = false;
    fetchDemoStatus()
      .then((s) => {
        if (!cancelled) setStatus(s);
      })
      .catch(() => {
        // Unknown is shown as nothing: the banner only ever appears when the server says so.
      });
    return () => {
      cancelled = true;
    };
  }, []);
  return status;
}

/** A small header pill that stays visible while the banner scrolls away; links back to it. */
export const DemoPill: React.FC<{ status: DemoStatus | null }> = ({ status }) =>
  status?.demo_mode ? (
    <a href="#demo-banner" className="demo-pill" title={status.banner ?? "Demo mode"}>
      Demo
    </a>
  ) : null;

/**
 * The DEMO MODE banner and its "What is simulated?" panel. Rendered only when the server
 * reports demo mode, so a real deployment never shows it and a demo never hides it.
 */
export const DemoBanner: React.FC<{ status: DemoStatus | null }> = ({ status }) => {
  const [open, setOpen] = useState(false);
  if (!status?.demo_mode) return null;
  const simulated = status.simulated.filter((s) => s.status === "SIMULATED");
  const real = status.simulated.filter((s) => s.status !== "SIMULATED");
  return (
    <div id="demo-banner" className="demo-banner" role="note" aria-label="Demo mode notice">
      <div className="demo-banner-row">
        {/* The server's own wording, verbatim (it already begins "DEMO MODE"). */}
        <strong className="demo-banner-text">{status.banner}</strong>
        <button
          type="button"
          className="btn btn-ghost btn-compact"
          aria-expanded={open}
          aria-controls="demo-simulated-panel"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? "Hide details" : "What is simulated?"}
        </button>
      </div>
      {open && (
        <div id="demo-simulated-panel" className="demo-simulated">
          <p>
            This server runs the demo kit. Nothing here concerns a real patient. The list below comes from the running
            server, so it reflects its actual configuration.
          </p>
          <div className="demo-simulated-grid">
            {[
              { title: "Simulated", items: simulated },
              { title: "Real", items: real },
            ].map((group) =>
              group.items.length > 0 ? (
                <div key={group.title}>
                  <h4>{group.title}</h4>
                  <ul>
                    {group.items.map((s) => (
                      <li key={s.item}>
                        <span className={TONE_CLASS[simulatedTone(s.status)]}>
                          {s.status === "SIMULATED" ? "Simulated" : s.status === "REAL" ? "Real" : "Real · rule-based"}
                        </span>
                        <strong>{s.item}</strong>
                        <span>{s.detail}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null
            )}
          </div>
        </div>
      )}
    </div>
  );
};
