"use client";

import { useLanguage } from "../../shell/ShellProvider";
import { PUBLIC_LANGUAGE_NOTICE } from "./publicNav";

/**
 * Public pages are server-rendered in English. When the visitor switches the UI to Hindi or
 * Marathi, say so instead of leaving them to wonder why the page did not change. The only client
 * code on otherwise static pages; it imports the two notice strings, never the page copy.
 */
export function PublicLanguageNotice() {
  const [lang] = useLanguage();
  if (lang === "en") return null;
  return (
    <p className="pub-notice" role="status" lang={lang}>
      {PUBLIC_LANGUAGE_NOTICE[lang]}
    </p>
  );
}
