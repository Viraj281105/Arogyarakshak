import Link from "next/link";
import type { Metadata } from "next";
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
          <Link href="/" className="btn btn-primary btn-lg">
            Go to the home page
          </Link>
          <Link href="/#intake-dropzone" className="btn btn-ghost btn-lg">
            Check a document
          </Link>
        </>
      }
    >
      <p>
        The link may be mistyped or out of date. ArogyaRakshak has two places to go: the home page, where you check a bill,
        insurer letter or prescription, and the <Link href="/clinical-review">clinical reviewer workspace</Link>.
      </p>
      <p>
        If you were in the middle of a check: its access key is kept only in the memory of the tab where you started it, so
        a new page load cannot reopen that case.
      </p>
    </StatusPage>
  );
}
