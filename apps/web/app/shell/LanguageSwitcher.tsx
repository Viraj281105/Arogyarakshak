"use client";

import React from "react";
import { LANGUAGES } from "../shared/i18n/types";
import { useLanguage } from "./ShellProvider";
import { HTML_LANG, LANGUAGE_LABELS, shellCopy } from "./shellCopy";

/** EN / हिंदी / मराठी segmented switch. Each label carries its own `lang` for correct shaping. */
export function LanguageSwitcher({ className = "" }: { className?: string }) {
  const [lang, setLang] = useLanguage();
  return (
    <div className={`site-lang ${className}`} role="group" aria-label={shellCopy[lang].language.label}>
      {LANGUAGES.map((l) => (
        <button
          key={l}
          type="button"
          lang={HTML_LANG[l]}
          className="site-lang-btn"
          aria-pressed={lang === l}
          onClick={() => setLang(l)}
        >
          {LANGUAGE_LABELS[l]}
        </button>
      ))}
    </div>
  );
}
