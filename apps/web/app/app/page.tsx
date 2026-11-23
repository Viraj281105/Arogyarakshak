import type { Metadata } from "next";
import { HomeWorkspace } from "../components/HomeWorkspace";

export const metadata: Metadata = {
  title: "Case workspace — ArogyaRakshak",
  description: "Upload a hospital bill, insurer letter or prescription and run the five checks on one case.",
};

/**
 * The case workspace (Server Component shell; Wave 3 M2 moved it here from `/`). Upload, the case
 * desk and the five module tabs are the client HomeWorkspace; the page header is static.
 */
export default function WorkspacePage() {
  return (
    <HomeWorkspace
      header={
        <header className="workspace-head">
          <p className="lp-kicker">Case workspace</p>
          <h1 className="workspace-title">Check a document</h1>
          <p className="workspace-lede">
            Upload a hospital bill, insurer letter or prescription. Every check below reads the same case.
            The original file is read, then discarded.
          </p>
        </header>
      }
    />
  );
}
