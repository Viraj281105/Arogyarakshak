"use client";

import React, { useRef } from "react";
import Link from "next/link";
import { useScrollProgress } from "../../hooks/useScrollMotion";
import { HeroIllustration } from "./HeroIllustration";

const ASSURANCES = [
  {
    title: "Your original file is not kept",
    body: "It is read, then discarded. Extracted details stay until you delete the case.",
    icon: <path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6" />,
  },
  {
    title: "Nothing starts without consent",
    body: "The upload stays disabled until you tick the consent box yourself.",
    icon: <path d="M5 12.5l4.2 4.2L19 7" />,
  },
  {
    title: "Every finding shows its basis",
    body: "The reference rate or rule is shown beside it — or the line is marked as not compared.",
    icon: <path d="M4 5h11l5 5v9H4zM15 5v5h5M8 14h8M8 17h5" />,
  },
];

export const LandingHero: React.FC = () => {
  const ref = useRef<HTMLElement>(null);
  useScrollProgress(ref, "--hero-progress");

  return (
    <section ref={ref} className="lp-hero" aria-labelledby="lp-hero-title">
      <div className="lp-hero-copy">
        <p className="lp-eyebrow">
          <span className="lp-eyebrow-dot" aria-hidden="true" />
          Hospital bills · insurance denials · medicine prices
        </p>
        <h1 id="lp-hero-title" className="lp-display">
          Know what your hospital bill <em>should</em> cost.
        </h1>
        <p className="lp-lede">
          ArogyaRakshak reads a bill, insurer letter or prescription and checks it line by line against public CGHS
          rates, NPPA medicine price ceilings and IRDAI rules — then explains what it found in plain language.
        </p>
        <div className="lp-cta-row">
          <a href="#intake-dropzone" className="btn btn-primary btn-lg">
            Check a document
            <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
              <path d="M12 5v14M5 12l7 7 7-7" />
            </svg>
          </a>
          <a href="#lp-example" className="btn btn-ghost btn-lg">
            See an example first
          </a>
        </div>
        <ul className="lp-assurances">
          {ASSURANCES.map((a) => (
            <li key={a.title}>
              <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon lp-assurance-icon">
                {a.icon}
              </svg>
              <div>
                <strong>{a.title}</strong>
                <span>{a.body}</span>
              </div>
            </li>
          ))}
        </ul>
        <p className="lp-reviewer-note">
          Reviewing cases as a clinician?{" "}
          <Link href="/clinical-review">Open the reviewer workspace →</Link>
        </p>
      </div>
      <figure className="lp-hero-figure">
        <HeroIllustration />
        <figcaption>Illustration: a made-up bill, checked against real CGHS reference rates.</figcaption>
      </figure>
    </section>
  );
};
