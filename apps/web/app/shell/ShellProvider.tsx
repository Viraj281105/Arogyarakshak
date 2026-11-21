"use client";

import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import type { Language } from "../shared/i18n/types";
import { HTML_LANG } from "./shellCopy";
import { routeCommitted } from "./routeTransition";

type SetNode = (node: React.ReactNode) => void;

// Three contexts on purpose: pages read the language and call the (stable) slot setter; only the
// header reads the slot content. A page that fills the slot therefore never re-renders because
// the slot changed (one shared context would loop: render -> set slot -> new context -> render).
const LanguageContext = createContext<{ lang: Language; setLang: (lang: Language) => void }>({
  lang: "en",
  setLang: () => {},
});
const SlotSetterContext = createContext<SetNode>(() => {});
const SlotContentContext = createContext<React.ReactNode>(null);

/**
 * App-wide shell state. The language lives in memory only (as before WS4): persisting it would
 * need a pre-paint mechanism like the theme's to avoid an English flash and a layout shift.
 * Because the provider sits in the root layout, the choice survives client navigations.
 */
export function ShellProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLang] = useState<Language>("en");
  const [slot, setSlot] = useState<React.ReactNode>(null);
  const pathname = usePathname();

  // <html lang> follows the UI language: correct Devanagari shaping, hyphenation and voice.
  useEffect(() => {
    document.documentElement.lang = HTML_LANG[lang];
  }, [lang]);

  // A View Transition started by TransitionLink waits for this (see routeTransition.ts).
  useEffect(() => {
    routeCommitted();
  }, [pathname]);

  const language = useMemo(() => ({ lang, setLang }), [lang]);
  return (
    <LanguageContext.Provider value={language}>
      <SlotSetterContext.Provider value={setSlot}>
        <SlotContentContext.Provider value={slot}>{children}</SlotContentContext.Provider>
      </SlotSetterContext.Provider>
    </LanguageContext.Provider>
  );
}

/** Current UI language and its setter. */
export function useLanguage(): [Language, (lang: Language) => void] {
  const { lang, setLang } = useContext(LanguageContext);
  return [lang, setLang];
}

/** What pages have put into the header slot (read by SiteHeader only). */
export function useHeaderSlotContent(): React.ReactNode {
  return useContext(SlotContentContext);
}

/**
 * Puts page-specific chips (demo pill, signed-in reviewer) into the shared header while the
 * calling page is mounted, so that code stays in the routes that already ship it. Pass a
 * memoised node (useMemo) so the header only updates when the chip really changes.
 */
export function useHeaderSlot(node: React.ReactNode): void {
  const setSlot = useContext(SlotSetterContext);
  useEffect(() => {
    setSlot(node);
  }, [node, setSlot]);
  useEffect(() => () => setSlot(null), [setSlot]);
}
