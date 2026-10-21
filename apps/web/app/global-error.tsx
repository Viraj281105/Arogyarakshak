"use client"; // Error boundaries must be Client Components

import { useEffect } from "react";
import "./globals.css";
import { StatusPage } from "./components/StatusPage";

// Replaces the root layout when it fails, so it brings its own document, styles and the
// same pre-paint theme script as app/layout.tsx.
const THEME_SCRIPT = `(function(){var t="light";try{var s=localStorage.getItem("arogyarakshak_theme");if(s==="light"||s==="dark"){t=s;}else if(window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches){t="dark";}}catch(e){}document.documentElement.setAttribute("data-theme",t);})();`;

export default function GlobalError({ error, retry }: { error: unknown; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <title>Something went wrong — ArogyaRakshak</title>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <StatusPage
          code="Something went wrong"
          title="ArogyaRakshak could not load."
          variant="error"
          actions={
            <>
              <button type="button" className="btn btn-primary btn-lg" onClick={() => retry()}>
                Try again
              </button>
              {/* A full document load on purpose: the root layout itself failed. */}
              {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
              <a href="/" className="btn btn-ghost btn-lg">
                Reload the home page
              </a>
            </>
          }
        >
          <p>The application failed before the page could be drawn. Nothing was checked or saved by this failure.</p>
        </StatusPage>
      </body>
    </html>
  );
}
