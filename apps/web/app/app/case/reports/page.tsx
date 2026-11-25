import type { Metadata } from "next";
import { ReportsViewer } from "../../../components/workspace/ReportsViewer";
import { EvidenceVerificationIllustration } from "../../../components/illustrations/Illustrations";
import { serverT } from "../../../i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { tr } = await serverT();
  return { title: tr("Case reports — ArogyaRakshak"), description: tr("Appeal letter, pre-authorisation form, claim package and Claim Pack for the open case.") };
}

export default function ReportsPage() {
  return <ReportsViewer heroArt={<EvidenceVerificationIllustration size={96} />} />;
}
