"use client";

import React from "react";
import type { Language } from "../translations";
import { EXPLAIN_STRINGS } from "../lib/explainStrings";
import { describeExplanation, Explanation } from "../lib/explanation";

/**
 * "Why am I seeing this?" — a collapsed disclosure under a finding (ADR-017).
 *
 * Renders only what the server recorded: source evidence with its provenance class, the
 * exact rule or reference row used, the trust state, and what could not be determined.
 * Anything not recorded reads "not recorded". Uses a native <details>/<summary>, so it is
 * keyboard- and screen-reader-accessible without custom ARIA.
 */
export const ExplainTrail: React.FC<{ explanation?: Explanation | null; lang?: Language }> = ({
  explanation,
  lang = "en",
}) => {
  if (!explanation) return null;
  const s = EXPLAIN_STRINGS[lang] ?? EXPLAIN_STRINGS.en;
  const v = describeExplanation(explanation, lang);
  const h = { fontSize: "0.78rem", fontWeight: 700, margin: "0.6rem 0 0.2rem" } as const;
  const small = { fontSize: "0.8rem", margin: "0.1rem 0", overflowWrap: "anywhere" } as const;

  return (
    <details className="explain-trail" style={{ marginTop: "0.4rem", fontSize: "0.82rem" }}>
      <summary style={{ cursor: "pointer", minHeight: "1.5rem" }}>{s.summary}</summary>
      <div style={{ padding: "0.3rem 0.1rem 0.5rem" }}>
        <p style={{ ...small, fontWeight: 600 }}>{v.headline}</p>

        <h4 style={h}>{s.headingEvidence}</h4>
        {v.evidence.length === 0 ? (
          <p style={small}>{s.noEvidence}</p>
        ) : (
          <ul style={{ margin: 0, paddingLeft: "1.1rem" }}>
            {v.evidence.map((ev, i) => (
              <li key={i} style={small}>
                {ev.label}: <strong>{ev.value}</strong> — {ev.provenance}
                {ev.document !== null && (
                  <>
                    {" · "}
                    {s.document}: {ev.document}
                  </>
                )}
                {ev.sourceText && (
                  <>
                    {" · "}
                    {s.sourceText}: “{ev.sourceText}”
                  </>
                )}
              </li>
            ))}
          </ul>
        )}

        <h4 style={h}>{s.headingRule}</h4>
        {v.rules.length === 0 ? (
          <p style={small}>{s.noRule}</p>
        ) : (
          v.rules.map((r, i) => (
            <div key={i} style={{ marginBottom: "0.3rem" }}>
              <p style={{ ...small, fontWeight: 600 }}>
                {r.name}
                {r.source && (
                  <span style={{ fontWeight: 400 }}>
                    {" "}
                    ({s.source}: {r.source})
                  </span>
                )}
              </p>
              <dl style={{ margin: 0 }}>
                {r.facts.map((f, j) => (
                  <div key={j} style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                    <dt style={{ ...small, opacity: 0.85 }}>{f.label}:</dt>
                    <dd style={{ ...small, margin: 0, fontStyle: f.recorded ? "normal" : "italic" }}>{f.value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ))
        )}

        <h4 style={h}>{s.headingTrust}</h4>
        <p style={small}>
          {v.trust.label}
          {v.trust.detail ? ` — ${v.trust.detail}` : ""}
        </p>

        {v.undetermined.length > 0 && (
          <>
            <h4 style={h}>{s.headingUndetermined}</h4>
            <ul style={{ margin: 0, paddingLeft: "1.1rem" }}>
              {v.undetermined.map((u, i) => (
                <li key={i} style={small}>
                  {u}
                </li>
              ))}
            </ul>
          </>
        )}

        {v.notRecorded.length > 0 && (
          <>
            <h4 style={h}>{s.headingNotRecorded}</h4>
            <p style={small}>{v.notRecorded.join("; ")}</p>
          </>
        )}
        <p style={{ ...small, opacity: 0.75, marginTop: "0.5rem" }}>{s.noModel}</p>
        <p style={{ ...small, opacity: 0.75 }}>{explanation.disclaimer}</p>
      </div>
    </details>
  );
};
