import type { Metadata } from "next";
import { DocumentLink } from "./components/DocumentLink";
import { StatusPage } from "./components/StatusPage";
import { serverT } from "./i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { tr } = await serverT();
  return { title: tr("Page not found — ArogyaRakshak") };
}

/** 404 for unmatched URLs and notFound() calls. */
export default async function NotFound() {
  const { tr } = await serverT();
  return (
    <StatusPage
      code={tr("404 · Not found")}
      title={tr("There is no page at this address.")}
      variant="missing"
      actions={
        <>
          <DocumentLink href="/" className="btn btn-primary btn-lg">
            {tr("Go to the home page")}
          </DocumentLink>
          <DocumentLink href="/app#intake-dropzone" className="btn btn-ghost btn-lg">
            {tr("Check a document")}
          </DocumentLink>
        </>
      }
    >
      <p>
        {tr("The link may be mistyped or out of date. ArogyaRakshak has two places to go: the home page, and your case desk, where you check a bill, insurer letter or prescription.")}
      </p>
      <p>
        <DocumentLink href="/review">{tr("Clinical reviewer workspace")}</DocumentLink>
      </p>
      <p>{tr("Your cases stay in your account: open the case desk to continue where you were.")}</p>
    </StatusPage>
  );
}
