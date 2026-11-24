import type { Metadata } from "next";
import { CaseDesk } from "../components/workspace/CaseDesk";

export const metadata: Metadata = {
  title: "My cases — ArogyaRakshak",
  description: "Start a case from a hospital bill, insurer letter or prescription, or open one you already have.",
};

/** The case desk (Wave 3 M4). Server shell; the desk is a client component. */
export default function WorkspacePage() {
  return <CaseDesk />;
}
