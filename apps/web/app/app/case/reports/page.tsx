import type { Metadata } from "next";
import { ReportsViewer } from "../../../components/workspace/ReportsViewer";
import { EvidenceVerificationIllustration } from "../../../components/illustrations/Illustrations";

export const metadata: Metadata = {
  title: "Case reports — ArogyaRakshak",
  description: "Appeal letter, pre-authorisation form, claim package and Claim Pack for the open case.",
};

export default function ReportsPage() {
  return <ReportsViewer heroArt={<EvidenceVerificationIllustration size={96} />} />;
}
