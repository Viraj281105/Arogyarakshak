"use client";

import React, { useState } from "react";
import {
  ILLUSTRATIVE_LINES,
  IllustrativeLine,
  LineStatus,
  composeBill,
  formatINR,
} from "../../lib/illustrativeBill";
import { CGHS_VERSION } from "../../lib/referenceSnapshot";

const STATUS_LABEL: Record<LineStatus, string> = {
  overcharged: "Above reference",
  within_benchmark: "Within reference",
  bundled: "Usually included elsewhere",
  not_benchmarked: "Not compared",
};

const UNIT_LABEL: Record<string, string> = {
  per_day: "per day",
  per_visit: "per visit",
  per_service: "per test",
  per_session: "per session",
  per_shift: "per shift",
  per_bottle: "per bottle",
};

function explain(line: IllustrativeLine): string {
  const rate = line.rate;
  switch (line.status) {
    case "overcharged":
      return `Billed ${formatINR(line.billed)} against a CGHS reference of ${formatINR(line.reference ?? 0)} (${formatINR(rate?.rate ?? 0)} ${UNIT_LABEL[rate?.unit ?? ""] ?? ""}). The ${formatINR(line.billed - (line.reference ?? 0))} above it is what a BillNyay finding would point to — with the reference row shown, so you can check it.`;
    case "within_benchmark":
      return `Billed at or below the CGHS reference of ${formatINR(line.reference ?? 0)}. No finding is raised.`;
    case "bundled":
      return `The reference marks “${rate?.name ?? line.label}” as part of a larger charge (here, the room). Whether this hospital's package really includes it needs checking, so it is raised as a question to ask — not as a verdict.`;
    default:
      return `No row in the CGHS reference matches this line, so it is not compared at all. ${formatINR(line.billed)} is neither fair nor unfair as far as the tool can tell, and it is never compared against a guessed rate.`;
  }
}

const SCALE = Math.max(...ILLUSTRATIVE_LINES.map((l) => Math.max(l.billed, l.reference ?? 0)));
const pct = (n: number) => `${((n / SCALE) * 100).toFixed(2)}%`;

const LineBar: React.FC<{ line: IllustrativeLine }> = ({ line }) => {
  const ref = line.reference ?? 0;
  const base = line.status === "overcharged" ? ref : line.billed;
  return (
    <div className={`lp-bar lp-bar-${line.status}`} aria-hidden="true">
      <span className="lp-bar-base" style={{ width: pct(base) }} />
      {line.status === "overcharged" && (
        <span className="lp-bar-excess" style={{ left: pct(ref), width: pct(line.billed - ref) }} />
      )}
      {line.reference !== null && line.status !== "bundled" && (
        <span className="lp-bar-ref" style={{ left: pct(ref) }} />
      )}
    </div>
  );
};

export const WorkedExample: React.FC = () => {
  const [selected, setSelected] = useState<string>("ward");
  const line = ILLUSTRATIVE_LINES.find((l) => l.id === selected) ?? ILLUSTRATIVE_LINES[0];
  const c = composeBill(ILLUSTRATIVE_LINES);
  const segments = [
    { key: "within", label: "Within reference", value: c.withinReference },
    { key: "over", label: "Above reference", value: c.aboveReference },
    { key: "bundled", label: "Usually included elsewhere", value: c.bundled },
    { key: "unmatched", label: "Not compared", value: c.notCompared },
  ];

  return (
    <section id="lp-example" className="lp-section lp-example" aria-labelledby="lp-example-title">
      <header className="lp-section-head" data-reveal>
        <p className="lp-kicker">A worked example</p>
        <h2 id="lp-example-title" className="lp-heading">One bill, five lines, four possible answers.</h2>
        <p className="lp-section-lede">
          This bill is made up. The reference rates are the real {CGHS_VERSION} rows BillNyay uses, and each line gets
          the status the real audit would give it. Choose a line to see why.
        </p>
        <span className="lp-illustrative-pill">Illustrative — not a real patient&apos;s bill</span>
      </header>

      <div className="lp-example-grid" data-reveal>
        <div className="lp-example-lines" role="group" aria-label="Bill lines — choose one to see why">
          <div className="lp-example-legend" aria-hidden="true">
            <span><i className="lp-swatch lp-swatch-within" /> billed up to reference</span>
            <span><i className="lp-swatch lp-swatch-over" /> above reference</span>
            <span><i className="lp-swatch lp-swatch-ref" /> reference</span>
          </div>
          {ILLUSTRATIVE_LINES.map((l) => (
            <button
              key={l.id}
              type="button"
              aria-pressed={l.id === line.id}
              className={`lp-line ${l.id === line.id ? "is-selected" : ""}`}
              onClick={() => setSelected(l.id)}
            >
              <span className="lp-line-head">
                <span className="lp-line-label">
                  {l.label}
                  <small>{l.quantity}</small>
                </span>
                <span className="lp-line-amount code-tabular">{formatINR(l.billed)}</span>
              </span>
              <LineBar line={l} />
              <span className={`lp-status lp-status-${l.status}`}>{STATUS_LABEL[l.status]}</span>
            </button>
          ))}
        </div>

        <aside className="lp-example-detail" aria-live="polite">
          <p className="lp-kicker">Why this line</p>
          <h3>{line.label}</h3>
          <dl className="lp-detail-facts">
            <div>
              <dt>Billed</dt>
              <dd className="code-tabular">{formatINR(line.billed)}</dd>
            </div>
            <div>
              <dt>CGHS reference</dt>
              <dd className="code-tabular">
                {line.status === "not_benchmarked"
                  ? "no matching row"
                  : line.status === "bundled"
                    ? "included in room"
                    : formatINR(line.reference ?? 0)}
              </dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>
                <span className={`lp-status lp-status-${line.status}`}>{STATUS_LABEL[line.status]}</span>
              </dd>
            </div>
          </dl>
          <p className="lp-detail-body">{explain(line)}</p>
          {line.rate && (
            <p className="lp-detail-source">
              Reference row: <span className="code-tabular">{line.rate.name}</span>
            </p>
          )}
        </aside>
      </div>

      <figure className="lp-composition" data-reveal>
        <figcaption>
          <span>Where the {formatINR(c.billed)} goes</span>
          <span className="lp-composition-note">Share of the total billed amount</span>
        </figcaption>
        <div
          className="lp-composition-bar"
          role="img"
          aria-label={segments.map((s) => `${s.label} ${formatINR(s.value)}`).join(", ")}
        >
          {segments.map((s) => (
            <span
              key={s.key}
              className={`lp-seg lp-seg-${s.key}`}
              style={{ flexGrow: s.value }}
              title={`${s.label}: ${formatINR(s.value)}`}
            />
          ))}
        </div>
        <ul className="lp-composition-legend">
          {segments.map((s) => (
            <li key={s.key}>
              <i className={`lp-swatch lp-swatch-${s.key}`} aria-hidden="true" />
              <span>{s.label}</span>
              <strong className="code-tabular">{formatINR(s.value)}</strong>
            </li>
          ))}
        </ul>
        <p className="lp-composition-takeaway">
          On this bill, {formatINR(c.aboveReference)} sits above the CGHS reference, {formatINR(c.bundled)} is worth a
          question, and {formatINR(c.notCompared)} could not be checked — the tool says so instead of guessing.
        </p>
      </figure>
    </section>
  );
};
