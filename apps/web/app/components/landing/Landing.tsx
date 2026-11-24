"use client";

import React, { useRef } from "react";
import { useScrollReveal } from "../../hooks/useScrollMotion";
import { WorkedExample } from "./WorkedExample";

/**
 * The landing story (`/`), Wave 3 M3. Server-rendered sections arrive as slots (WS4: their content
 * ships no client JS); this wrapper adds the scroll reveal and the interactive worked example.
 * Order: hero, six capabilities, document-to-insight story, worked example, how it works, evidence,
 * reference coverage, privacy, languages, FAQ, call to action.
 *
 * English only: the Hindi and Marathi landing copy is pending native-speaker review
 * (components/public/publicCopy.ts); PublicLanguageNotice says so when hi or mr is selected.
 */
export const Landing: React.FC<{
  hero: React.ReactNode;
  journey: React.ReactNode;
  coverage: React.ReactNode;
  capabilities: React.ReactNode;
  steps: React.ReactNode;
  evidence: React.ReactNode;
  privacy: React.ReactNode;
  languages: React.ReactNode;
  faq: React.ReactNode;
  cta: React.ReactNode;
}> = ({ hero, journey, coverage, capabilities, steps, evidence, privacy, languages, faq, cta }) => {
  const ref = useRef<HTMLDivElement>(null);
  useScrollReveal(ref);
  return (
    <div ref={ref} className="lp">
      {hero}
      {capabilities}
      {journey}
      <WorkedExample />
      {steps}
      {evidence}
      {coverage}
      {privacy}
      {languages}
      {faq}
      {cta}
    </div>
  );
};
