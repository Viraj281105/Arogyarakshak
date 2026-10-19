"use client";

import React from "react";
import type { Language } from "../translations";
import { listenCopy } from "../lib/listenCopy";
import { setSimpleLanguage, useSimpleLanguage } from "../hooks/useListen";

/** Switch for the short plain-sentence variant of the read-aloud summaries. */
export const SimpleLanguageToggle: React.FC<{ lang: Language }> = ({ lang }) => {
  const simple = useSimpleLanguage();
  const ui = listenCopy[lang].ui;
  return (
    <label
      style={{ display: "flex", gap: "0.5rem", alignItems: "center", minHeight: "var(--min-touch-target, 44px)", justifyContent: "flex-end", fontSize: "0.9rem" }}
    >
      <input type="checkbox" checked={simple} onChange={(e) => setSimpleLanguage(e.target.checked)} aria-describedby="simple-language-help" />
      <span>{ui.simpleToggle}</span>
      <span id="simple-language-help" style={{ fontSize: "0.78rem", opacity: 0.8 }}>
        {ui.simpleToggleHelp}
      </span>
    </label>
  );
};
