"use client";

import React, { useRef } from "react";
import type { ModuleTab } from "../ModuleTabs";
import type { Translations } from "../../translations";
import { useScrollReveal } from "../../hooks/useScrollMotion";
import { LandingHero } from "./LandingHero";
import { CaseJourney } from "./CaseJourney";
import { WorkedExample } from "./WorkedExample";
import { ModuleOverview } from "./ModuleOverview";
import { ReferenceCoverage } from "./ReferenceCoverage";

/**
 * The landing story above the intake form. English only for now: the Hindi and Marathi
 * versions of this copy are pending native-speaker review (apps/web/AGENTS.md), so the
 * language switch currently changes the module names and descriptions here, not the prose.
 */
export const Landing: React.FC<{ t: Translations; onOpenModule: (tab: ModuleTab) => void }> = ({ t, onOpenModule }) => {
  const ref = useRef<HTMLDivElement>(null);
  useScrollReveal(ref);
  return (
    <div ref={ref} className="lp">
      <LandingHero />
      <CaseJourney />
      <WorkedExample />
      <ModuleOverview t={t} onOpen={onOpenModule} />
      <ReferenceCoverage />
    </div>
  );
};
