import React from "react";
import {
  CGHS_CATEGORY_COUNTS,
  CGHS_TOTAL_ROWS,
  CGHS_VERSION,
  LAW_LIBRARY,
  NPPA_REFERENCE_FORMULATIONS,
  SCHEMES,
} from "../../lib/referenceSnapshot";
import { serverT } from "../../i18n/server";

const MAX_ROWS = Math.max(...CGHS_CATEGORY_COUNTS.map((c) => c.rows));

/**
 * How much reference data this build really checks against. Every number comes from
 * lib/referenceSnapshot.ts, which a test keeps equal to the packaged data files.
 */
export async function ReferenceCoverage() {
  const { tr } = await serverT();
  return (
  <section className="lp-section lp-coverage" aria-labelledby="lp-coverage-title">
    <header className="lp-section-head" data-reveal>
      <p className="lp-kicker">{tr("What it checks against")}</p>
      <h2 id="lp-coverage-title" className="lp-heading">{tr("A small, honest reference set — counted, not claimed.")}</h2>
      <p className="lp-section-lede">
        {tr("These are the reference tables in this build. They are deliberately small curated subsets, so a line or medicine outside them is reported as not checked rather than matched to something close.")}
      </p>
    </header>

    <div className="lp-coverage-grid">
      <figure className="lp-coverage-card lp-coverage-cghs" data-reveal>
        <div className="lp-coverage-figure">
          <span className="lp-big-number code-tabular">{CGHS_TOTAL_ROWS}</span>
          <span className="lp-big-label">
            {tr("CGHS reference rows")}
            <small>{tr("{version} · {count} categories", { version: CGHS_VERSION, count: CGHS_CATEGORY_COUNTS.length })}</small>
          </span>
        </div>
        <ul className="lp-hbars" aria-label={tr("CGHS reference rows per category")}>
          {CGHS_CATEGORY_COUNTS.map((c, i) => (
            <li key={c.category} style={{ "--i": i } as React.CSSProperties}>
              <span className="lp-hbar-label">{c.category}</span>
              <span className="lp-hbar-track" aria-hidden="true">
                <span className="lp-hbar-fill" style={{ width: `${(c.rows / MAX_ROWS) * 100}%` }} />
              </span>
              <span className="lp-hbar-value code-tabular">{c.rows}</span>
            </li>
          ))}
        </ul>
        <figcaption>{tr("Rows per category in billnyay/data/cghs_rates.json.")}</figcaption>
      </figure>

      <div className="lp-coverage-side">
        <figure className="lp-coverage-card" data-reveal>
          <div className="lp-coverage-figure">
            <span className="lp-big-number code-tabular">{LAW_LIBRARY.total}</span>
            <span className="lp-big-label">
              {tr("Legal provisions appeal drafts may cite")}
              <small>
                {tr("{verified} checked against a primary source · {open} not yet", { verified: LAW_LIBRARY.verified, open: LAW_LIBRARY.total - LAW_LIBRARY.verified })}
              </small>
            </span>
          </div>
          <div
            className="lp-verify-bar"
            role="img"
            aria-label={tr("{verified} of {total} provisions verified against a primary source", { verified: LAW_LIBRARY.verified, total: LAW_LIBRARY.total })}
          >
            {Array.from({ length: LAW_LIBRARY.total }, (_, i) => (
              <span key={i} className={i < LAW_LIBRARY.verified ? "is-verified" : "is-unverified"} />
            ))}
          </div>
          <figcaption>{tr("Each provision carries its verification status with it; an unverified one is not presented as settled law.")}</figcaption>
        </figure>

        <div className="lp-coverage-pair">
          <figure className="lp-coverage-card lp-coverage-mini" data-reveal>
            <span className="lp-big-number code-tabular">{NPPA_REFERENCE_FORMULATIONS}</span>
            <figcaption>{tr("NPPA Schedule-I formulations in DawaCheck's curated subset")}</figcaption>
          </figure>
          <figure className="lp-coverage-card lp-coverage-mini" data-reveal>
            <span className="lp-big-number code-tabular">{SCHEMES.length}</span>
            <figcaption>{tr("Government schemes whose eligibility rules SchemeSetu evaluates: {schemes}", { schemes: SCHEMES.join(", ") })}</figcaption>
          </figure>
        </div>
      </div>
    </div>
  </section>
  );
}
