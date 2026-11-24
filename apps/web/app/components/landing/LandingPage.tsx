"use client";

import React, { useMemo } from "react";
import { DemoBanner, DemoPill, useDemoStatus } from "../demo/DemoBanner";
import { useHeaderSlot } from "../../shell/ShellProvider";
import { PublicLanguageNotice } from "../public/PublicLanguageNotice";
import { Landing } from "./Landing";

/**
 * The public landing page (`/`). Every section except the worked example is a Server Component
 * rendered by app/page.tsx and passed in as a slot, so their content ships no client JS (WS4).
 * Wave 3 M3: the page no longer imports the full translations dictionary (it only needed the
 * module names, which now come from the server-rendered capability overview).
 */
export function LandingPage({
  hero,
  journey,
  coverage,
  capabilities,
  steps,
  evidence,
  privacy,
  languages,
  faq,
  cta,
}: {
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
}) {
  const demoStatus = useDemoStatus();
  useHeaderSlot(useMemo(() => <DemoPill status={demoStatus} />, [demoStatus]));
  return (
    <>
      <div className="lp-backdrop" aria-hidden="true" />
      <div className="container">
        <DemoBanner status={demoStatus} />
        <PublicLanguageNotice />
        <Landing
          hero={hero}
          journey={journey}
          coverage={coverage}
          capabilities={capabilities}
          steps={steps}
          evidence={evidence}
          privacy={privacy}
          languages={languages}
          faq={faq}
          cta={cta}
        />
      </div>
    </>
  );
}
