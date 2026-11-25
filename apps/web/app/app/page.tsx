import type { Metadata } from "next";
import { CaseDesk } from "../components/workspace/CaseDesk";
import { DocumentIntelligenceBackground } from "../components/illustrations/Backgrounds";
import { DocumentScanIllustration } from "../components/illustrations/Illustrations";
import { serverT } from "../i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { tr } = await serverT();
  return { title: tr("My cases — ArogyaRakshak"), description: tr("Start a case from a hospital bill, insurer letter or prescription, or open one you already have.") };
}

/** The case desk (Wave 3 M4). Server shell passes static SVG slots so illustrations cost zero client JS. */
export default function WorkspacePage() {
  return (
    <CaseDesk
      intakeBg={<DocumentIntelligenceBackground intensity={0.3} />}
      intakeArt={<DocumentScanIllustration size={112} animate />}
    />
  );
}
