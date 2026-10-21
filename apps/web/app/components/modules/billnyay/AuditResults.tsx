"use client";

import React from "react";
import { Language, translations } from "../../../translations";
import { ExplainTrail } from "../../ExplainTrail";
import type { AuditResponse, AuditResultItem } from "./types";

const inr = (n: number) => `₹${n.toLocaleString("en-IN")}`;

/**
 * Where each rupee of the bill falls, from the per-line statuses the server returned.
 * Unlike `potential_savings` (a net figure over compared lines), this keeps a line billed
 * below its reference from hiding another line billed above one.
 */
export function composeAudit(items: AuditResultItem[]) {
  const c = { within: 0, above: 0, bundled: 0, notCompared: 0 };
  for (const row of items) {
    if (!row.benchmarked || row.cghs_benchmark === null) c.notCompared += row.charged;
    else if (row.status === "bundled") c.bundled += row.charged;
    else {
      c.within += Math.min(row.charged, row.cghs_benchmark);
      c.above += Math.max(0, row.charged - row.cghs_benchmark);
    }
  }
  return c;
}

/** CGHS audit totals, where the bill's money falls, and every line with its reference,
 *  status and "Why am I seeing this?" trail. An unmatched line is never shown as fair. */
export function AuditResults({ audit, currentLang }: { audit: AuditResponse; currentLang: Language }) {
  const t = translations[currentLang].modules.billnyay;
  const c = composeAudit(audit.audit_items);
  const scale = Math.max(1, ...audit.audit_items.map((r) => Math.max(r.charged, r.cghs_benchmark ?? 0)));
  const pct = (n: number) => `${((n / scale) * 100).toFixed(2)}%`;
  const segments = [
    { key: "within", label: t.fairBadge, value: c.within },
    { key: "over", label: t.overchargedBadge, value: c.above },
    { key: "bundled", label: "Usually included elsewhere", value: c.bundled },
    { key: "unmatched", label: t.notBenchmarkedBadge, value: c.notCompared },
  ].filter((s) => s.value > 0);

  return (
    <section className="bn-audit" aria-labelledby="bn-audit-title">
      <h3 id="bn-audit-title" className="sr-only">
        CGHS audit result
      </h3>

      <div className="bn-stats">
        <div className="bn-stat">
          <span className="bn-stat-label">{t.chargedTotal}</span>
          <span className="bn-stat-value code-tabular">{inr(audit.total_charged)}</span>
          <span className="bn-stat-sub">{audit.audit_items.length} line(s) read from the bill</span>
        </div>
        <div className="bn-stat">
          <span className="bn-stat-label">{t.cghsBenchmark}</span>
          <span className="bn-stat-value code-tabular">{inr(audit.total_benchmark)}</span>
          <span className="bn-stat-sub">
            {audit.benchmarked_count} line(s) compared, billed at {inr(audit.benchmarked_charged)}
          </span>
        </div>
        <div className={`bn-stat ${audit.potential_savings > 0 ? "is-flagged" : ""}`}>
          <span className="bn-stat-label">{t.potentialSavings}</span>
          <span className="bn-stat-value code-tabular">{inr(audit.potential_savings)}</span>
          <span className="bn-stat-sub">Net, across compared lines only</span>
        </div>
      </div>

      {audit.total_charged > 0 && segments.length > 0 && (
        <figure className="lp-composition bn-composition">
          <figcaption>
            <span>Where the {inr(audit.total_charged)} falls</span>
            <span className="lp-composition-note">By each line&apos;s status</span>
          </figcaption>
          <div
            className="lp-composition-bar"
            role="img"
            aria-label={segments.map((s) => `${s.label} ${inr(s.value)}`).join(", ")}
          >
            {segments.map((s) => (
              <span key={s.key} className={`lp-seg lp-seg-${s.key}`} style={{ flexGrow: s.value }} title={`${s.label}: ${inr(s.value)}`} />
            ))}
          </div>
          <ul className="lp-composition-legend">
            {segments.map((s) => (
              <li key={s.key}>
                <i className={`lp-swatch lp-swatch-${s.key}`} aria-hidden="true" />
                <span>{s.label}</span>
                <strong className="code-tabular">{inr(s.value)}</strong>
              </li>
            ))}
          </ul>
        </figure>
      )}

      {/* Coverage disclosure: the patient must be able to see how much of the
          bill was actually compared against a benchmark. */}
      {audit.unmatched_count > 0 && (
        <div className="bn-notice is-warning" role="note">
          {t.unmatchedNotice
            .replace("{count}", String(audit.unmatched_count))
            .replace("{amount}", inr(audit.unmatched_amount))}
        </div>
      )}

      {audit.audit_items.length > 0 ? (
        <>
          <div className="bn-lines-head">
            <h4>{t.overchargesTitle}</h4>
            <span className="timeline-count">{audit.deviations_count} flagged</span>
          </div>
          <ul className="bn-lines">
            {audit.audit_items.map((row, idx) => {
              const benchmarked = row.benchmarked && row.cghs_benchmark !== null;
              const ref = row.cghs_benchmark ?? 0;
              const status = !benchmarked ? "not_benchmarked" : row.status;
              const over = benchmarked && row.status === "overcharged";
              return (
                <li key={idx} className="bn-line">
                  <div className="bn-line-head">
                    <strong className="bn-line-name">{row.item_name}</strong>
                    <span className="bn-line-amount code-tabular">{inr(row.charged)}</span>
                  </div>
                  <div className={`lp-bar lp-bar-${status}`} aria-hidden="true">
                    <span className="lp-bar-base" style={{ width: pct(over ? ref : row.charged) }} />
                    {over && <span className="lp-bar-excess" style={{ left: pct(ref), width: pct(row.charged - ref) }} />}
                    {benchmarked && row.status !== "bundled" && <span className="lp-bar-ref" style={{ left: pct(ref) }} />}
                  </div>
                  <div className="bn-line-foot">
                    <span className="bn-line-ref">
                      {benchmarked ? (
                        <>
                          {t.cghsCol}: <span className="code-tabular">{inr(ref)}</span>
                          {row.benchmark_basis && <> · {row.benchmark_basis}</>}
                          {over && (
                            <>
                              {" · "}
                              <span className="bn-line-excess code-tabular">
                                +{inr(row.charged - ref)} ({row.deviation_percentage}%)
                              </span>
                            </>
                          )}
                        </>
                      ) : (
                        row.not_benchmarked_reason ?? t.notBenchmarked
                      )}
                    </span>
                    <span className={`lp-status lp-status-${status}`}>
                      {!benchmarked
                        ? t.notBenchmarkedBadge
                        : row.status === "bundled"
                          ? t.bundledBadge
                          : row.is_deviation
                            ? t.overchargedBadge
                            : t.fairBadge}
                    </span>
                  </div>
                  {row.explanation && <ExplainTrail explanation={row.explanation} lang={currentLang} />}
                </li>
              );
            })}
          </ul>
        </>
      ) : (
        <div className="bn-notice">No billing line items were found in the uploaded document for audit comparison.</div>
      )}

      {audit.deviations_count > 0 && <div className="bn-notice is-guidance">{t.disputeGrounds}</div>}
    </section>
  );
}
