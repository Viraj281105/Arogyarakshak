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

/**
 * The DEMO MODE banner and its "What is simulated?" panel. Rendered only when the server
 * reports demo mode, so a real deployment never shows it and a demo never hides it.
 */
export const DemoBanner: React.FC<{ status: DemoStatus | null }> = ({ status }) => {
  const [open, setOpen] = useState(false);
  if (!status?.demo_mode) return null;
  return (
    <div className="demo-banner" role="note" aria-label="Demo mode notice">
      <div className="demo-banner-row">
        <strong>{status.banner}</strong>
        <button
          type="button"
          className="btn btn-secondary btn-compact"
          aria-expanded={open}
          aria-controls="demo-simulated-panel"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? "Hide details" : "What is simulated?"}
        </button>
      </div>
      {open && (
        <div id="demo-simulated-panel" className="demo-simulated">
          <p style={{ margin: "0 0 0.5rem" }}>
            This server runs the demo kit. Nothing here concerns a real patient. The list below comes from the running
            server, so it reflects its actual configuration.
          </p>
          <ul>
            {status.simulated.map((s) => (
              <li key={s.item}>
                <span className={TONE_CLASS[simulatedTone(s.status)]}>
                  {s.status === "SIMULATED" ? "Simulated" : s.status === "REAL" ? "Real" : "Real · rule-based"}
                </span>{" "}
                <strong>{s.item}</strong> — {s.detail}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
