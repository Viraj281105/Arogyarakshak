"use client"; // Error boundaries must be Client Components

import { useEffect, useState } from "react";
import "./globals.css";
import { StatusPage } from "./components/StatusPage";
import { LANGUAGE_COOKIE, parseLanguage, translator, type Dictionary } from "./i18n/format";
import { loadDictionary } from "./i18n/load";
import type { Language } from "./shared/i18n/types";

// Replaces the root layout when it fails, so it brings its own document, styles and the
// same pre-paint theme script as app/layout.tsx. With no layout there is no language provider
// either: it reads the language cookie itself.
const THEME_SCRIPT = `(function(){var t="light";try{var s=localStorage.getItem("arogyarakshak_theme");if(s==="light"||s==="dark"){t=s;}else if(window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches){t="dark";}}catch(e){}document.documentElement.setAttribute("data-theme",t);})();`;

function cookieLanguage(): Language {
  if (typeof document === "undefined") return "en";
  return parseLanguage(document.cookie.match(new RegExp(`(?:^|; )${LANGUAGE_COOKIE}=([a-z]+)`))?.[1]);
}

export default function GlobalError({ error, retry }: { error: unknown; retry: () => void }) {
  const [language] = useState<Language>(cookieLanguage);
  const [dictionary, setDictionary] = useState<Dictionary>();
  useEffect(() => {
    console.error(error);
  }, [error]);
  useEffect(() => {
    loadDictionary(language)
      .then(setDictionary)
      .catch(() => undefined);
  }, [language]);
  const tr = translator(dictionary);

  return (
    <html lang={dictionary ? language : "en"} suppressHydrationWarning>
      <head>
        <title>{tr("Something went wrong — ArogyaRakshak")}</title>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <StatusPage
          standalone
          code={tr("Something went wrong")}
          title={tr("ArogyaRakshak could not load.")}
          variant="error"
          actions={
            <>
              <button type="button" className="btn btn-primary btn-lg" onClick={() => retry()}>
                {tr("Try again")}
              </button>
              {/* A full document load on purpose: the root layout itself failed. */}
              {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
              <a href="/" className="btn btn-ghost btn-lg">
                {tr("Reload the home page")}
              </a>
            </>
          }
        >
          <p>{tr("The application failed before the page could be drawn. Nothing was checked or saved by this failure.")}</p>
        </StatusPage>
      </body>
    </html>
  );
}
