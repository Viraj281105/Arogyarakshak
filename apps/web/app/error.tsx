"use client"; // Error boundaries must be Client Components

import Link from "next/link";
import { useEffect } from "react";
import { StatusPage } from "./components/StatusPage";

/** Error boundary for every route under the root layout (Next 16 passes `retry`). */
// Not named `Error`: that would shadow the global used in the instanceof check below.
export default function RouteError({ error, retry }: { error: unknown; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  // Server errors carry a digest that matches the server log; no message is shown, so
  // nothing internal reaches the page.
  const digest = error instanceof Error && "digest" in error ? String((error as Error & { digest?: string }).digest ?? "") : "";

  return (
    <StatusPage
      code="Something went wrong"
      title="This page could not be shown."
      variant="error"
      actions={
        <>
          <button type="button" className="btn btn-primary btn-lg" onClick={() => retry()}>
            Try again
          </button>
          <Link href="/" className="btn btn-ghost btn-lg">
            Go to the home page
          </Link>
        </>
      }
    >
      <p>
        Part of the page failed while loading. Nothing on it is shown as finished or checked. Trying again often works; if
        it keeps happening, the API may be unreachable.
      </p>
      {digest && (
        <p className="bn-fine">
          Reference for the server log: <code>{digest}</code>
        </p>
      )}
    </StatusPage>
  );
}
