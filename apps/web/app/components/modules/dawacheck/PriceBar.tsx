import React from "react";
import type { PriceCheck, PriceCheckView } from "../../../lib/dawacheck";

const rupees = (n: number) => `₹${n.toFixed(2)}`;

/**
 * Per-unit price against the NPPA ceiling, on one scale. Draws only what the server
 * compared: without a per-unit price (CANNOT_COMPARE) only the ceiling is shown.
 */
export const PriceBar: React.FC<{ check: PriceCheck; view: PriceCheckView }> = ({ check, view }) => {
  const unit = check.unit_label || "unit";
  const ceiling = check.nppa_ceiling_price;
  const billed = view.verdict === "cannot_compare" ? null : (check.billed_unit_price ?? null);
  const scale = Math.max(ceiling, billed ?? 0) * 1.15 || 1;
  const pct = (n: number) => `${((n / scale) * 100).toFixed(2)}%`;
  const over = billed !== null && billed > ceiling;

  return (
    <figure className="dc-bar">
      <div
        className={`lp-bar dc-track ${billed === null ? "lp-bar-not_benchmarked" : over ? "lp-bar-overcharged" : "lp-bar-within_benchmark"}`}
        role="img"
        aria-label={
          billed === null
            ? `Not compared. NPPA ceiling ${rupees(ceiling)} per ${unit}.`
            : `Paid ${rupees(billed)} per ${unit}; NPPA ceiling ${rupees(ceiling)} per ${unit}.`
        }
      >
        {billed !== null && <span className="lp-bar-base" style={{ width: pct(over ? ceiling : billed) }} />}
        {over && billed !== null && <span className="lp-bar-excess" style={{ left: pct(ceiling), width: pct(billed - ceiling) }} />}
        <span className="lp-bar-ref" style={{ left: pct(ceiling) }} />
      </div>
      <figcaption className="dc-bar-legend">
        <span>
          {billed === null ? "Paid per " + unit + ": not established" : <>Paid per {unit}: <strong className="code-tabular">{rupees(billed)}</strong></>}
        </span>
        <span>
          <i className="lp-swatch lp-swatch-ref" aria-hidden="true" /> NPPA ceiling: <strong className="code-tabular">{rupees(ceiling)}</strong>
        </span>
      </figcaption>
    </figure>
  );
};
