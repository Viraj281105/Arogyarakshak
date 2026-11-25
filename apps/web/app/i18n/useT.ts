"use client";

import { useEffect, useMemo, useSyncExternalStore } from "react";
import { useLanguage } from "../shell/ShellProvider";
import type { Language } from "../shared/i18n/types";
import { translator, type Dictionary, type Translate } from "./format";
import { loadDictionary } from "./load";

const loaded = new Map<Language, Dictionary>();
const pending = new Set<Language>();
const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function load(lang: Language): void {
  if (lang === "en" || loaded.has(lang) || pending.has(lang)) return;
  pending.add(lang);
  loadDictionary(lang)
    .then((dictionary) => {
      if (dictionary) loaded.set(lang, dictionary);
      listeners.forEach((l) => l());
    })
    // A failed chunk leaves the English text on screen; the next mount tries again.
    .catch(() => undefined)
    .finally(() => pending.delete(lang));
}

/**
 * `tr` for client components. The server render and hydration use English (the dictionary is a
 * separate chunk), then the chosen language replaces it as soon as it has loaded.
 */
export function useT(): Translate {
  const [lang] = useLanguage();
  const dictionary = useSyncExternalStore(
    subscribe,
    () => loaded.get(lang),
    () => undefined,
  );
  useEffect(() => load(lang), [lang]);
  return useMemo(() => translator(dictionary), [dictionary]);
}
