import Link from "next/link";
import React from "react";

/**
 * Shared layout for the not-found and error pages. No hooks, so it renders from Server
 * and Client Components alike, including global-error, which replaces the root layout.
 */
export const StatusPage: React.FC<{
  code: string;
  title: string;
  children: React.ReactNode;
  actions: React.ReactNode;
  variant: "missing" | "error";
}> = ({ code, title, children, actions, variant }) => (
  <div className="status-page">
    <div className="lp-backdrop" aria-hidden="true" />
    <header className="header-bar">
      <div className="container header-inner">
        <Link href="/" className="rv-back">
          <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
            <path d="M19 12H5M11 6l-6 6 6 6" />
          </svg>
          ArogyaRakshak
        </Link>
      </div>
    </header>
    <main className="container status-main">
      <div className="status-copy">
        <p className="lp-kicker">{code}</p>
        <h1 className="lp-display status-title">{title}</h1>
        <div className="status-body">{children}</div>
        <div className="lp-cta-row">{actions}</div>
      </div>
      <figure className="status-figure" aria-hidden="true">
        <svg viewBox="0 0 320 340" className="status-ill" focusable="false">
          <rect className="ill-sheet-back" x="44" y="30" width="250" height="290" rx="16" transform="rotate(4 169 175)" />
          <rect className="ill-sheet" x="24" y="18" width="260" height="296" rx="16" />
          <rect className="ill-sheet-margin" x="24" y="18" width="6" height="296" rx="3" />
          <text className="ill-kicker" x="50" y="54">{variant === "missing" ? "ADDRESS" : "THIS PAGE"}</text>
          <line className="ill-rule" x1="50" x2="258" y1="70" y2="70" />
          {[0, 1, 2].map((i) => (
            <g key={i} className="status-ill-row">
              <rect className="status-ill-text" x="50" y={96 + i * 48} width={i === 1 ? 120 : 150} height="9" rx="4.5" />
              <rect className="status-ill-text is-soft" x="50" y={112 + i * 48} width="80" height="7" rx="3.5" />
              <g className="ill-mark ill-mark-within" style={{ "--row": i } as React.CSSProperties}>
                <circle cx="244" cy={104 + i * 48} r="10" />
                <path d={`M239 ${104 + i * 48} l3.5 3.5 l6.5 -7`} />
              </g>
            </g>
          ))}
          <rect className="status-ill-missing" x="44" y="236" width="222" height="52" rx="10" />
          <text className="ill-label" x="58" y="259">
            {variant === "missing" ? "No matching row" : "Could not be read"}
          </text>
          <text className="ill-sub" x="58" y="277">
            {variant === "missing" ? "— so nothing is guessed" : "— nothing shown as done"}
          </text>
          {variant === "missing" ? (
            <g className="ill-mark ill-mark-unmatched" style={{ "--row": 3 } as React.CSSProperties}>
              <circle cx="244" cy="262" r="11" />
              <path d="M239 262 H249" />
            </g>
          ) : (
            <g className="ill-mark ill-mark-over" style={{ "--row": 3 } as React.CSSProperties}>
              <circle cx="244" cy="262" r="11" />
              <path d="M244 256 V264 M244 268 v0.5" />
            </g>
          )}
        </svg>
      </figure>
    </main>
  </div>
);
