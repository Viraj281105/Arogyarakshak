import React from "react";
import { TransitionLink } from "../../shell/TransitionLink";
import { publicCopy } from "../public/publicCopy";
import { ScrollProgressSection } from "./ScrollProgressSection";
import { HeroIllustration } from "./HeroIllustration";

const ASSURANCE_ICONS = [
  <path key="0" d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6" />,
  <path key="1" d="M5 12.5l4.2 4.2L19 7" />,
  <path key="2" d="M4 5h11l5 5v9H4zM15 5v5h5M8 14h8M8 17h5" />,
];

/** Server Component (WS4): static hero copy; only the scroll-progress wrapper is client code. */
export const LandingHero: React.FC = () => {
  const c = publicCopy().landing;
  return (
    <ScrollProgressSection progressVar="--hero-progress" className="lp-hero" labelledBy="lp-hero-title">
      <div className="lp-hero-copy">
        <p className="lp-eyebrow">
          <span className="lp-eyebrow-dot" aria-hidden="true" />
          {c.eyebrow}
        </p>
        <h1 id="lp-hero-title" className="lp-display">
          {c.headlineLead} <em>{c.headlineEmphasis}</em>
        </h1>
        <p className="lp-lede">{c.lede}</p>
        <div className="lp-cta-row">
          <TransitionLink href={c.primaryCta.href} className="btn btn-primary btn-lg">
            {c.primaryCta.label}
            <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </TransitionLink>
          <TransitionLink href={c.secondaryCta.href} className="btn btn-ghost btn-lg">
            {c.secondaryCta.label}
          </TransitionLink>
        </div>
        <ul className="lp-assurances">
          {c.assurances.map((a, i) => (
            <li key={a.title}>
              <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon lp-assurance-icon">
                {ASSURANCE_ICONS[i]}
              </svg>
              <div>
                <strong>{a.title}</strong>
                <span>{a.body}</span>
              </div>
            </li>
          ))}
        </ul>
        <p className="lp-reviewer-note">
          {c.reviewerNote} <TransitionLink href={c.reviewerLink.href}>{c.reviewerLink.label} →</TransitionLink>
        </p>
      </div>
      <figure className="lp-hero-figure">
        <HeroIllustration />
        <figcaption>{c.figureCaption}</figcaption>
      </figure>
    </ScrollProgressSection>
  );
};
