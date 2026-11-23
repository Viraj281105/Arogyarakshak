import { CaseJourney } from "./components/landing/CaseJourney";
import { LandingHero } from "./components/landing/LandingHero";
import { LandingPage } from "./components/landing/LandingPage";
import { ReferenceCoverage } from "./components/landing/ReferenceCoverage";

/**
 * Public landing route (Server Component). The case workspace lives at /app (Wave 3 M2). The static
 * landing sections render here on the server and are passed into the client LandingPage as slots,
 * so they add no client JS (WS4 bundle budget).
 */
export default function HomePage() {
  return <LandingPage hero={<LandingHero />} journey={<CaseJourney />} coverage={<ReferenceCoverage />} />;
}
