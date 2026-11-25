"use client";

import { useLanguage } from "../../shell/ShellProvider";
import { PUBLIC_LANGUAGE_NOTICE } from "./publicNav";

/**
 * Says that the Hindi or Marathi text is machine translated and not yet reviewed by a native
 * speaker (docs/localization.md). It imports the two notice strings, never the page copy.
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
