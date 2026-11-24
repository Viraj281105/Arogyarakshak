import type { Metadata } from "next";
import { CaseOverview } from "../../components/workspace/CaseOverview";
import { DocumentIntelligenceBackground } from "../../components/illustrations/Backgrounds";
import { DocumentScanIllustration, OcrIllustration } from "../../components/illustrations/Illustrations";

export const metadata: Metadata = {
  title: "Case overview — ArogyaRakshak",
  description: "The open case: next steps, documents kept, timeline and evidence graph.",
};

export default function CaseOverviewPage() {
  return (
    <CaseOverview
      heroBg={<DocumentIntelligenceBackground intensity={0.35} />}
      heroArt={<DocumentScanIllustration size={120} animate />}
      docsEmptyArt={<OcrIllustration size={112} />}
    />
  );
}
