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
import { useT } from "../../i18n/useT";
import { msg, type Translate } from "../../i18n/format";

const STATUS_LABEL: Record<LineStatus, string> = {
  overcharged: msg("Above reference"),
  within_benchmark: msg("Within reference"),
  bundled: msg("Usually included elsewhere"),
  not_benchmarked: msg("Not compared"),
};

const UNIT_LABEL: Record<string, string> = {
  per_day: msg("per day"),
  per_visit: msg("per visit"),
  per_service: msg("per test"),
  per_session: msg("per session"),
  per_shift: msg("per shift"),
  per_bottle: msg("per bottle"),
};

function explain(line: IllustrativeLine, tr: Translate): string {
  const rate = line.rate;
  switch (line.status) {
    case "overcharged":
      return tr(
        "Billed {billed} against a CGHS reference of {reference} ({rate} {unit}). The {excess} above it is what a BillNyay finding would point to — with the reference row shown, so you can check it.",
        {
          billed: formatINR(line.billed),
          reference: formatINR(line.reference ?? 0),
          rate: formatINR(rate?.rate ?? 0),
          unit: tr(UNIT_LABEL[rate?.unit ?? ""] ?? ""),
          excess: formatINR(line.billed - (line.reference ?? 0)),
        },
      );
    case "within_benchmark":
      return tr("Billed at or below the CGHS reference of {reference}. No finding is raised.", { reference: formatINR(line.reference ?? 0) });
    case "bundled":
      return tr(
        "The reference marks “{name}” as part of a larger charge (here, the room). Whether this hospital's package really includes it needs checking, so it is raised as a question to ask — not as a verdict.",
        { name: rate?.name ?? line.label },
      );
    default:
      return tr(
        "No row in the CGHS reference matches this line, so it is not compared at all. {billed} is neither fair nor unfair as far as the tool can tell, and it is never compared against a guessed rate.",
        { billed: formatINR(line.billed) },
      );
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
  const tr = useT();
  const [selected, setSelected] = useState<string>("ward");
  const line = ILLUSTRATIVE_LINES.find((l) => l.id === selected) ?? ILLUSTRATIVE_LINES[0];
  const c = composeBill(ILLUSTRATIVE_LINES);
  const segments = [
    { key: "within", label: tr("Within reference"), value: c.withinReference },
    { key: "over", label: tr("Above reference"), value: c.aboveReference },
    { key: "bundled", label: tr("Usually included elsewhere"), value: c.bundled },
    { key: "unmatched", label: tr("Not compared"), value: c.notCompared },
  ];

  return (
    <section id="lp-example" className="lp-section lp-example" aria-labelledby="lp-example-title">
      <header className="lp-section-head" data-reveal>
        <p className="lp-kicker">{tr("A worked example")}</p>
        <h2 id="lp-example-title" className="lp-heading">{tr("One bill, five lines, four possible answers.")}</h2>
        <p className="lp-section-lede">{tr("This bill is made up. The reference rates are the real {CGHS_VERSION} rows BillNyay uses, and each line gets the status the real audit would give it. Choose a line to see why.", { CGHS_VERSION: CGHS_VERSION })}</p>
        <span className="lp-illustrative-pill">{tr("Synthetic example — not a real patient's bill")}</span>
      </header>

      <div className="lp-example-grid" data-reveal>
        <div className="lp-example-lines" role="group" aria-label={tr("Bill lines — choose one to see why")}>
          <div className="lp-example-legend" aria-hidden="true">
            <span><i className="lp-swatch lp-swatch-within" />{" "}{tr("billed up to reference")}</span>
            <span><i className="lp-swatch lp-swatch-over" />{" "}{tr("above reference")}</span>
            <span><i className="lp-swatch lp-swatch-ref" />{" "}{tr("reference")}</span>
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
              <span className={`lp-status lp-status-${l.status}`}>{tr(STATUS_LABEL[l.status])}</span>
            </button>
          ))}
        </div>

        <aside className="lp-example-detail" aria-live="polite">
          <p className="lp-kicker">{tr("Why this line")}</p>
          <h3>{line.label}</h3>
          <dl className="lp-detail-facts">
            <div>
              <dt>{tr("Billed")}</dt>
              <dd className="code-tabular">{formatINR(line.billed)}</dd>
            </div>
            <div>
              <dt>{tr("CGHS reference")}</dt>
              <dd className="code-tabular">
                {line.status === "not_benchmarked"
                  ? tr("no matching row")
                  : line.status === "bundled"
                    ? tr("included in room")
                    : formatINR(line.reference ?? 0)}
              </dd>
            </div>
            <div>
              <dt>{tr("Status")}</dt>
              <dd>
                <span className={`lp-status lp-status-${line.status}`}>{tr(STATUS_LABEL[line.status])}</span>
              </dd>
            </div>
          </dl>
          <p className="lp-detail-body">{explain(line, tr)}</p>
          {line.rate && (
            <p className="lp-detail-source">{tr("Reference row:")}{" "}<span className="code-tabular">{line.rate.name}</span>
            </p>
          )}
        </aside>
      </div>

      <figure className="lp-composition" data-reveal>
        <figcaption>
          <span>{tr("Where the {value} goes", { value: formatINR(c.billed) })}</span>
          <span className="lp-composition-note">{tr("Share of the total billed amount")}</span>
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
        <p className="lp-composition-takeaway">{tr("On this bill, {value} sits above the CGHS reference, {value2} is worth a question, and {value3} could not be checked — the tool says so instead of guessing.", { value: formatINR(c.aboveReference), value2: formatINR(c.bundled), value3: formatINR(c.notCompared) })}</p>
      </figure>
    </section>
  );
};
