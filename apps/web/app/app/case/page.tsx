import type { Metadata } from "next";
import { CaseOverview } from "../../components/workspace/CaseOverview";
import { DocumentIntelligenceBackground } from "../../components/illustrations/Backgrounds";
import { DocumentScanIllustration, OcrIllustration } from "../../components/illustrations/Illustrations";
import { serverT } from "../../i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { tr } = await serverT();
  return { title: tr("Case overview — ArogyaRakshak"), description: tr("The open case: next steps, documents kept, timeline and evidence graph.") };
}

export default function CaseOverviewPage() {
  return (
    <CaseOverview
      heroBg={<DocumentIntelligenceBackground intensity={0.35} />}
      heroArt={<DocumentScanIllustration size={120} animate />}
      docsEmptyArt={<OcrIllustration size={112} />}
    />
  );
}
