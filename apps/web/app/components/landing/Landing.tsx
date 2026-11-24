"use client";

import React, { useRef } from "react";
import type { Translations } from "../../translations";
import { useScrollReveal } from "../../hooks/useScrollMotion";
import { WorkedExample } from "./WorkedExample";
import { ModuleOverview } from "./ModuleOverview";

/**
 * The landing story (`/`). Module cards link into the workspace at `/app#module-<id>`. English only for now: the Hindi and Marathi
 * versions of this copy are pending native-speaker review (apps/web/AGENTS.md), so the
 * language switch currently changes the module names and descriptions here, not the prose.
 *
 * WS4: the static sections (hero, journey, reference coverage) are Server Components rendered by
 * app/page.tsx and passed in as slots, so their content ships no client JS; only the worked
 * example (interactive) and the module cards (language + tab opening) are client code.
 */
export const Landing: React.FC<{
  t: Translations;
  hero: React.ReactNode;
  journey: React.ReactNode;
  coverage: React.ReactNode;
}> = ({ t, hero, journey, coverage }) => {
  const ref = useRef<HTMLDivElement>(null);
  useScrollReveal(ref);
  return (
    <div ref={ref} className="lp">
      {hero}
      {journey}
      <WorkedExample />
      <ModuleOverview t={t} />
      {coverage}
    </div>
  );
};
