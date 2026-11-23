"use client";

import React, { useMemo } from "react";
import { DemoBanner, DemoPill, useDemoStatus } from "../demo/DemoBanner";
import { useHeaderSlot, useLanguage } from "../../shell/ShellProvider";
import { translations } from "../../translations";
import { Landing } from "./Landing";

/**
 * The public landing page (`/`). Wave 3 M2 moved the case workspace to `/app`; this keeps the
 * landing content that `/` showed before (it is redesigned in M3). The static sections are Server
 * Components rendered by app/page.tsx and passed in as slots, so they ship no client JS (WS4).
 */
export function LandingPage({
  hero,
  journey,
  coverage,
}: {
  hero: React.ReactNode;
  journey: React.ReactNode;
  coverage: React.ReactNode;
}) {
  const [currentLang] = useLanguage();
  const demoStatus = useDemoStatus();
  useHeaderSlot(useMemo(() => <DemoPill status={demoStatus} />, [demoStatus]));
  return (
    <>
      <div className="lp-backdrop" aria-hidden="true" />
      <div className="container">
        <DemoBanner status={demoStatus} />
        <Landing t={translations[currentLang]} hero={hero} journey={journey} coverage={coverage} />
      </div>
    </>
  );
}
