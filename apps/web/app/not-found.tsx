import type { Metadata } from "next";
import { DocumentLink } from "./components/DocumentLink";
import { StatusPage } from "./components/StatusPage";

export const metadata: Metadata = {
  title: "Page not found — ArogyaRakshak",
};

/** 404 for unmatched URLs and notFound() calls. */
export default function NotFound() {
  return (
    <StatusPage
      code="404 · Not found"
      title="There is no page at this address."
      variant="missing"
      actions={
        <>
          <DocumentLink href="/" className="btn btn-primary btn-lg">
            Go to the home page
          </DocumentLink>
          <DocumentLink href="/app#intake-dropzone" className="btn btn-ghost btn-lg">
            Check a document
          </DocumentLink>
        </>
      }
    >
      <p>
        The link may be mistyped or out of date. ArogyaRakshak has two places to go: the home page, where you check a bill,
        insurer letter or prescription, and the <DocumentLink href="/review">clinical reviewer workspace</DocumentLink>.
      </p>
      <p>
        If you were in the middle of a check: its access key is kept only in the memory of the tab where you started it, so
        a new page load cannot reopen that case.
      </p>
    </StatusPage>
  );
}
