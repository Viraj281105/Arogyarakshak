import type { Metadata } from "next";
import { CaseJourney } from "./components/landing/CaseJourney";
import { LandingHero } from "./components/landing/LandingHero";
import { LandingPage } from "./components/landing/LandingPage";
import {
  LandingCapabilities,
  LandingCta,
  LandingEvidence,
  LandingFaq,
  LandingLanguages,
  LandingPrivacy,
  LandingSteps,
} from "./components/landing/LandingSections";
import { ReferenceCoverage } from "./components/landing/ReferenceCoverage";
import { localisedPublicCopy } from "./components/public/publicCopy";
import { requestLanguage } from "./i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { meta } = (await localisedPublicCopy(await requestLanguage())).landing;
  return { title: meta.title, description: meta.description };
}

/**
 * Public landing route (Server Component). The case workspace lives at /app (Wave 3 M2). The static
 * landing sections render here on the server and are passed into the client LandingPage as slots,
 * so they add no client JS (WS4 bundle budget). Wave 3 M3 added the capability overview, how it
 * works, evidence, privacy, languages, FAQ and closing call to action.
 */
export default function HomePage() {
  return (
    <LandingPage hero={<LandingHero />} journey={<CaseJourney />} coverage={<ReferenceCoverage />}
      capabilities={<LandingCapabilities />}
      steps={<LandingSteps />}
      evidence={<LandingEvidence />}
      privacy={<LandingPrivacy />}
      languages={<LandingLanguages />}
      faq={<LandingFaq />}
      cta={<LandingCta />}
    />
  );
}
