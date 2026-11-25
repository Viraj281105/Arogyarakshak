/**
 * Interface strings keyed by their English sentence, as on the web (docs/localization.md):
 *
 *   tr('Delete {count} cases', { count })      // reads the current language when called
 *   useTranslation();                          // in every component that renders tr() text
 *   msg('Not found')                           // marks a string kept in a constant, shown later
 *
 * `tr` is not a hook, so event handlers and services always get the language in force when they
 * run. `useTranslation` is what makes a component draw again after the language changes.
 *
 * Write whole sentences: word order differs between the languages. A missing translation shows
 * the English sentence. Hindi and Marathi are machine translations awaiting native review.
 */
import { useSyncExternalStore } from 'react';
import { getLanguage, subscribeLanguage } from '../services/languageStore';
import type { Language } from './strings';
import { UI } from './ui';

export type Vars = Record<string, string | number>;
export type Translate = (key: string, vars?: Vars) => string;

/** Identity. Marks an English string that is passed to `tr(...)` somewhere else. */
export const msg = <K extends string>(key: K): K => key;

/** Replaces {name} placeholders. An unknown placeholder is left as written. */
export function format(template: string, vars?: Vars): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (whole, name: string) => (name in vars ? String(vars[name]) : whole));
}

export const tr: Translate = (key, vars) => {
  const language: Language = getLanguage();
  const entry = language === 'en' ? undefined : UI[key];
  return format(entry?.[language === 'hi' ? 0 : 1] || key, vars);
};

export function useTranslation(): Language {
  return useSyncExternalStore(subscribeLanguage, getLanguage, getLanguage);
}
