"use client";

import React, { useRef } from "react";
import { useScrollProgress } from "../../hooks/useScrollMotion";

// What actually happens to a document, in order. Each claim here is backed by code:
// the 10 MB limit (apps/api config max_upload_bytes), English OCR (kadi/ocr), identifier
// redaction of the stored excerpt (kadi/redaction.py), in-browser AES-GCM for the claim
// pack (lib/packageCrypto.ts) and patient-initiated deletion (SEC-03).
const STEPS = [
  {
    title: "You add a document",
    body: "A photo, PDF or text export of a bill, discharge summary, insurer letter or prescription — up to 10 MB. Nothing is sent until you tick consent.",
    facts: ["JPG · PNG · PDF · TXT · CSV", "Consent is opt-in"],
    icon: <path d="M12 16V4M7 9l5-5 5 5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />,
  },
  {
    title: "Kadi reads it",
    body: "Scans are read with English text recognition; line items, amounts, dates and names are pulled out. Direct identifiers are stripped from the excerpt that is kept, and the file itself is discarded.",
    facts: ["Original file discarded", "Identifiers redacted"],
    icon: <path d="M4 6h16M4 10h10M4 14h16M4 18h7M17 15l3 3" />,
  },
  {
    title: "The modules check the case",
    body: "Charges are compared with CGHS rates, medicines with NPPA ceilings, denials with IRDAI rules, and your details with PM-JAY and MJPJAY eligibility rules. Anything without a reference is reported as not compared.",
    facts: ["Rule-based comparisons", "No guessed benchmarks"],
    icon: <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />,
  },
  {
    title: "You decide what to do next",
    body: "Read each finding with its basis, edit the appeal drafts, and download a claim pack — password-protected in your browser if you want. Delete the case whenever you like.",
    facts: ["Editable drafts", "Delete any time"],
    icon: <path d="M5 4h10l4 4v12H5zM9 12h6M9 16h4" />,
  },
];

export const CaseJourney: React.FC = () => {
  const ref = useRef<HTMLElement>(null);
  useScrollProgress(ref, "--journey-progress");

  return (
    <section ref={ref} className="lp-section lp-journey" aria-labelledby="lp-journey-title">
      <header className="lp-section-head" data-reveal>
        <p className="lp-kicker">How a case moves</p>
        <h2 id="lp-journey-title" className="lp-heading">From a folded bill to a clear next step.</h2>
      </header>
      <div className="lp-journey-track">
        {/* The connector behind the markers fills as the section scrolls through view. */}
        <ol className="lp-journey-steps">
          {STEPS.map((s, i) => (
            <li key={s.title} className="lp-journey-step" data-reveal style={{ "--i": i } as React.CSSProperties}>
              <div className="lp-journey-marker">
                <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
                  {s.icon}
                </svg>
              </div>
              <span className="lp-journey-num" aria-hidden="true">
                0{i + 1}
              </span>
              <h3>{s.title}</h3>
              <p>{s.body}</p>
              <ul className="lp-chips" aria-label="Key facts">
                {s.facts.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
};
