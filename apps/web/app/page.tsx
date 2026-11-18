import { HomeWorkspace } from "./components/HomeWorkspace";
import { CaseJourney } from "./components/landing/CaseJourney";
import { LandingHero } from "./components/landing/LandingHero";
import { ReferenceCoverage } from "./components/landing/ReferenceCoverage";

/**
 * Home route (Server Component). The static landing sections render here on the server and are
 * passed into the interactive workspace as slots, so they add no client JS (WS4 bundle budget).
 */
export default function HomePage() {
  return <HomeWorkspace hero={<LandingHero />} journey={<CaseJourney />} coverage={<ReferenceCoverage />} />;
}
