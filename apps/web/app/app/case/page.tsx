import type { Metadata } from "next";
import { CaseOverview } from "../../components/workspace/CaseOverview";

export const metadata: Metadata = {
  title: "Case overview — ArogyaRakshak",
  description: "The open case: next steps, documents kept, timeline and evidence graph.",
};

export default function CaseOverviewPage() {
  return <CaseOverview />;
}
