import React from "react";
import { EvidenceBadge } from "./Badges";
import { T } from "../../i18n/T";

/**
 * Hand-built SVG chart primitives (Wave 3 decision D3: no chart library). Server-safe, no JS.
 * Every chart:
 * - requires `source`, `units` and `period`, shown in its caption, so no figure floats free;
 * - can carry a `basis` ("estimate" | "verified") label;
 * - renders its data as a real table in a disclosure (the accessible alternative), and the SVG
 *   has role="img" with a text summary;
 * - uses chart tokens (chart-series-1..6, chart-within/over/bundled/unmatched), AA-checked >= 3:1.
 * Labels are HTML, not SVG text, so they stay readable at 360 px.
 */

export type ChartTone = "within" | "over" | "bundled" | "unmatched" | 1 | 2 | 3 | 4 | 5 | 6;

export interface ChartMeta {
  title: string;
  source: string;
  units: string;
  period: string;
  basis?: "estimate" | "verified";
  /** Number formatter for values; defaults to en-IN grouping. */
  format?: (n: number) => string;
}

const defaultFormat = (n: number) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(n);
const toneClass = (t: ChartTone | undefined, i: number) => `ui-tone-${t ?? ((i % 6) + 1)}`;

function ChartFrame({
  meta,
  summary,
  children,
  table,
}: {
  meta: ChartMeta;
  summary: string;
  children: React.ReactNode;
  table: { head: React.ReactNode[]; rows: (string | number)[][] };
}) {
  return (
    <figure className="ui-chart">
      <figcaption className="ui-chart-head">
        <span className="ui-chart-title">{meta.title}</span>
        {meta.basis === "verified" ? (
          <EvidenceBadge state="verified" size="sm" />
        ) : meta.basis === "estimate" ? (
          <span className="ui-badge ui-badge-sm ui-estimate-badge">
            <T k="Estimate" />
          </span>
        ) : null}
      </figcaption>
      <div className="ui-chart-body" role="img" aria-label={`${meta.title}. ${summary}`}>
        {children}
      </div>
      <p className="ui-chart-meta">
        <T k="Units: {units} · Period: {period} · Source: {source}" vars={{ units: meta.units, period: meta.period, source: meta.source }} />
      </p>
      <details className="ui-chart-data">
        <summary>
          <T k="Data table" />
        </summary>
        <div className="ui-table-scroll" tabIndex={0} role="region" aria-label={meta.title}>
          <table className="ui-table">
            <caption className="sr-only">
              {meta.title} ({meta.units}, {meta.period})
            </caption>
            <thead>
              <tr>
                {table.head.map((h, i) => (
                  <th key={i} scope="col">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((r, i) => (
                <tr key={i}>
                  {r.map((c, j) =>
                    j === 0 ? (
                      <th key={j} scope="row">
                        {c}
                      </th>
                    ) : (
                      <td key={j} className="is-num code-tabular">
                        {c}
                      </td>
                    ),
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}

const pct = (v: number, max: number) => (max > 0 ? Math.max(0, (v / max) * 100) : 0);

export interface BarDatum {
  label: string;
  value: number;
  tone?: ChartTone;
}

/** Horizontal bars (one row per item). Negative values are not supported: use WaterfallChart. */
export function BarChart({ data, ...meta }: ChartMeta & { data: readonly BarDatum[] }) {
  const f = meta.format ?? defaultFormat;
  const max = Math.max(0, ...data.map((d) => d.value));
  return (
    <ChartFrame
      meta={meta}
      summary={data.map((d) => `${d.label}: ${f(d.value)} ${meta.units}`).join("; ")}
      table={{ head: [<T key="item" k="Item" />, meta.units], rows: data.map((d) => [d.label, f(d.value)]) }}
    >
      <ul className="ui-bars" aria-hidden="true">
        {data.map((d, i) => (
          <li key={d.label}>
            <span className="ui-bar-label">{d.label}</span>
            <svg className="ui-bar-track" viewBox="0 0 100 10" preserveAspectRatio="none">
              <rect width="100" height="10" className="ui-track" />
              <rect width={pct(d.value, max)} height="10" className={toneClass(d.tone, i)} />
            </svg>
            <span className="ui-bar-value code-tabular">{f(d.value)}</span>
          </li>
        ))}
      </ul>
    </ChartFrame>
  );
}

export interface StackSeries {
  key: string;
  label: string;
  tone?: ChartTone;
}

/** Horizontal stacked bars with a legend; each row's total is shown. */
export function StackedBarChart({
  series,
  rows,
  ...meta
}: ChartMeta & { series: readonly StackSeries[]; rows: readonly { label: string; values: Record<string, number> }[] }) {
  const f = meta.format ?? defaultFormat;
  const totals = rows.map((r) => series.reduce((s, k) => s + Math.max(0, r.values[k.key] ?? 0), 0));
  const max = Math.max(0, ...totals);
  return (
    <ChartFrame
      meta={meta}
      summary={rows.map((r, i) => `${r.label}: total ${f(totals[i])} ${meta.units}`).join("; ")}
      table={{
        head: [<T key="item" k="Item" />, ...series.map((s) => s.label), <T key="total" k="Total" />],
        rows: rows.map((r, i) => [r.label, ...series.map((s) => f(r.values[s.key] ?? 0)), f(totals[i])]),
      }}
    >
      <Legend items={series.map((s, i) => ({ label: s.label, cls: toneClass(s.tone, i) }))} />
      <ul className="ui-bars" aria-hidden="true">
        {rows.map((r, ri) => {
          let x = 0;
          return (
            <li key={r.label}>
              <span className="ui-bar-label">{r.label}</span>
              <svg className="ui-bar-track" viewBox="0 0 100 10" preserveAspectRatio="none">
                <rect width="100" height="10" className="ui-track" />
                {series.map((s, si) => {
                  const w = pct(Math.max(0, r.values[s.key] ?? 0), max);
                  const rect = <rect key={s.key} x={x} width={w} height="10" className={toneClass(s.tone, si)} />;
                  x += w;
                  return rect;
                })}
              </svg>
              <span className="ui-bar-value code-tabular">{f(totals[ri])}</span>
            </li>
          );
        })}
      </ul>
    </ChartFrame>
  );
}

function Legend({ items }: { items: { label: string; cls: string; value?: string }[] }) {
  return (
    <ul className="ui-legend" aria-hidden="true">
      {items.map((it) => (
        <li key={it.label}>
          <svg width="12" height="12" viewBox="0 0 12 12">
            <rect width="12" height="12" rx="3" className={it.cls} />
          </svg>
          {it.label}
          {it.value && <span className="code-tabular"> {it.value}</span>}
        </li>
      ))}
    </ul>
  );
}

/** Pure: donut arc segments as [start, end] fractions of the circle. Zero/negative values get no arc. */
export function donutSegments(values: readonly number[]): [number, number][] {
  const clean = values.map((v) => (Number.isFinite(v) && v > 0 ? v : 0));
  const total = clean.reduce((a, b) => a + b, 0);
  let at = 0;
  return clean.map((v) => {
    const start = at;
    at += total > 0 ? v / total : 0;
    return [start, at];
  });
}

/** Share of a whole. Use only when the parts really add up to a meaningful total. */
export function DonutChart({ data, centerLabel, ...meta }: ChartMeta & { data: readonly BarDatum[]; centerLabel?: string }) {
  const f = meta.format ?? defaultFormat;
  const total = data.reduce((s, d) => s + Math.max(0, d.value), 0);
  const segs = donutSegments(data.map((d) => d.value));
  const R = 40;
  const C = 2 * Math.PI * R;
  const share = (v: number) => (total > 0 ? `${Math.round((Math.max(0, v) / total) * 100)}%` : "0%");
  return (
    <ChartFrame
      meta={meta}
      summary={`${f(total)} ${meta.units}. ` + data.map((d) => `${d.label}: ${f(d.value)} (${share(d.value)})`).join("; ")}
      table={{ head: [<T key="part" k="Part" />, meta.units, <T key="share" k="Share" />], rows: data.map((d) => [d.label, f(d.value), share(d.value)]) }}
    >
      <div className="ui-donut">
        <svg viewBox="0 0 100 100" aria-hidden="true">
          <circle cx="50" cy="50" r={R} className="ui-track-stroke" fill="none" strokeWidth="14" />
          {segs.map(([a, b], i) =>
            b > a ? (
              <circle
                key={data[i].label}
                cx="50"
                cy="50"
                r={R}
                fill="none"
                strokeWidth="14"
                className={`${toneClass(data[i].tone, i)} ui-stroke`}
                strokeDasharray={`${(b - a) * C} ${C}`}
                strokeDashoffset={-a * C}
                transform="rotate(-90 50 50)"
              />
            ) : null,
          )}
        </svg>
        <div className="ui-donut-center" aria-hidden="true">
          <span className="code-tabular">{f(total)}</span>
          <small>{centerLabel ?? meta.units}</small>
        </div>
      </div>
      <Legend items={data.map((d, i) => ({ label: d.label, cls: toneClass(d.tone, i), value: `${f(d.value)} · ${share(d.value)}` }))} />
    </ChartFrame>
  );
}

export interface WaterfallStep {
  label: string;
  /** Change from the previous running total; for `total` steps, ignored (the running total is drawn). */
  value: number;
  total?: boolean;
}

/** Pure: each step's [from, to] given a starting total. */
export function waterfallSpans(start: number, steps: readonly WaterfallStep[]): { from: number; to: number }[] {
  let run = start;
  return steps.map((s) => {
    if (s.total) return { from: 0, to: run };
    const from = run;
    run += s.value;
    return { from, to: run };
  });
}

/** From a starting amount through additions and deductions to an end amount (e.g. billed -> payable). */
export function WaterfallChart({
  start,
  startLabel,
  steps,
  ...meta
}: ChartMeta & { start: number; startLabel: string; steps: readonly WaterfallStep[] }) {
  const f = meta.format ?? defaultFormat;
  const all: WaterfallStep[] = [{ label: startLabel, value: start, total: true }, ...steps];
  const spans = [{ from: 0, to: start }, ...waterfallSpans(start, steps)];
  const max = Math.max(1, ...spans.flatMap((s) => [s.from, s.to]));
  const min = Math.min(0, ...spans.flatMap((s) => [s.from, s.to]));
  const H = 160;
  const y = (v: number) => H - ((v - min) / (max - min)) * H;
  const W = 56;
  return (
    <ChartFrame
      meta={meta}
      summary={all.map((s, i) => `${s.label}: ${s.total ? f(spans[i].to) : (s.value >= 0 ? "+" : "") + f(s.value)}`).join("; ")}
      table={{
        head: [
          <T key="step" k="Step" />,
          <T key="change" k="Change ({units})" vars={{ units: meta.units }} />,
          <T key="running" k="Running total ({units})" vars={{ units: meta.units }} />,
        ],
        rows: all.map((s, i) => [s.label, s.total ? "—" : (s.value >= 0 ? "+" : "") + f(s.value), f(spans[i].to)]),
      }}
    >
      <div className="ui-chart-scroll">
        <div className="ui-waterfall" style={{ minWidth: `${all.length * 4.5}rem` }}>
          <svg viewBox={`0 0 ${all.length * W} ${H}`} preserveAspectRatio="none" aria-hidden="true" className="ui-waterfall-svg">
            <line x1="0" x2={all.length * W} y1={y(0)} y2={y(0)} className="ui-axis" />
            {all.map((s, i) => {
              const { from, to } = spans[i];
              const top = y(Math.max(from, to));
              const h = Math.max(1, Math.abs(y(from) - y(to)));
              const cls = s.total ? "ui-tone-2" : s.value < 0 ? "ui-tone-1" : "ui-tone-4";
              return <rect key={s.label} x={i * W + 8} width={W - 16} y={top} height={h} rx="2" className={cls} />;
            })}
          </svg>
          <ol className="ui-waterfall-labels" aria-hidden="true">
            {all.map((s, i) => (
              <li key={s.label}>
                <span className="code-tabular">{s.total ? f(spans[i].to) : (s.value >= 0 ? "+" : "") + f(s.value)}</span>
                <small>{s.label}</small>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </ChartFrame>
  );
}

export interface TimelineEvent {
  /** ISO date (YYYY-MM-DD) or date-time. */
  date: string;
  label: string;
  detail?: string;
}

/** Events on a time axis (positions are proportional to time) with a numbered, readable list. */
export function TimelineChart({ events, locale = "en-IN", ...meta }: Omit<ChartMeta, "format"> & { events: readonly TimelineEvent[]; locale?: string }) {
  const sorted = [...events].sort((a, b) => Date.parse(a.date) - Date.parse(b.date));
  const t = sorted.map((e) => Date.parse(e.date));
  const t0 = Math.min(...t);
  const t1 = Math.max(...t);
  const x = (v: number) => (t1 > t0 ? 4 + ((v - t0) / (t1 - t0)) * 92 : 50);
  const fmt = (iso: string) => new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(iso));
  return (
    <ChartFrame
      meta={{ ...meta, format: undefined }}
      summary={sorted.map((e) => `${fmt(e.date)}: ${e.label}`).join("; ")}
      table={{ head: [<T key="date" k="Date" />, <T key="event" k="Event" />, <T key="detail" k="Detail" />], rows: sorted.map((e) => [fmt(e.date), e.label, e.detail ?? ""]) }}
    >
      <svg viewBox="0 0 100 14" className="ui-timeline-svg" aria-hidden="true">
        <line x1="2" x2="98" y1="7" y2="7" className="ui-axis" />
        {sorted.map((e, i) => (
          <g key={`${e.date}-${i}`}>
            <circle cx={x(t[i])} cy="7" r="2.6" className="ui-tone-1" />
            <text x={x(t[i])} y="8.1" textAnchor="middle" className="ui-timeline-num">
              {i + 1}
            </text>
          </g>
        ))}
      </svg>
      <ol className="ui-timeline-list" aria-hidden="true">
        {sorted.map((e, i) => (
          <li key={`${e.date}-${i}`}>
            <span className="ui-timeline-index">{i + 1}</span>
            <time dateTime={e.date}>{fmt(e.date)}</time> <strong>{e.label}</strong>
            {e.detail && <span className="ui-timeline-detail">{e.detail}</span>}
          </li>
        ))}
      </ol>
    </ChartFrame>
  );
}
