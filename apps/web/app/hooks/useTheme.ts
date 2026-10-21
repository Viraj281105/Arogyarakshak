"use client";

import { useCallback, useSyncExternalStore } from "react";

type Theme = "dark" | "light";
const STORAGE_KEY = "arogyarakshak_theme";

// The pre-paint script in app/layout.tsx sets <html data-theme> from the saved choice, else
// the OS preference, else light. This hook only reads and changes that attribute, so the
// server render ("light") and the first client render agree and nothing flashes.
function readTheme(): Theme {
  return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
}

function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}

/** Light/dark theme. A per-viewer convenience only, so storage failures are ignored. */
export function useTheme() {
  const theme = useSyncExternalStore<Theme>(subscribe, readTheme, () => "light");

  const toggleTheme = useCallback(() => {
    const next: Theme = readTheme() === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Ignore
    }
  }, []);

  return { theme, toggleTheme };
}
