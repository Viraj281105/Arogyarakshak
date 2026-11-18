"use client";

import React from "react";
import { useTheme } from "../hooks/useTheme";
import { useLanguage } from "./ShellProvider";
import { shellCopy } from "./shellCopy";

/** Light/dark switch. The pre-paint script in layout.tsx sets the initial theme. */
export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const [lang] = useLanguage();
  const label = theme === "dark" ? shellCopy[lang].theme.toLight : shellCopy[lang].theme.toDark;
  return (
    <button type="button" className="site-icon-btn" onClick={toggleTheme} aria-label={label} title={label}>
      <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" className="site-icon">
        {theme === "dark" ? (
          <>
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
          </>
        ) : (
          <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />
        )}
      </svg>
    </button>
  );
}
