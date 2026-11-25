// UI strings use the English sentence as the key (gettext style):
//
//   const tr = useT();                       // client components (./useT)
//   const tr = await serverT();              // Server Components (./server)
//   tr("Delete {count} cases", { count })    // placeholders are {names}
//   msg("Not found")                         // marks a string kept in a constant, translated later
//
// Hindi and Marathi live in ./locales/{hi,mr}.ts. tests/i18n.test.ts fails when a key used by
// the code is missing from either language or its placeholders differ. A missing key shows the
// English sentence, never a blank or a key name.

import type { Language } from "../shared/i18n/types";

export type Dictionary = Readonly<Record<string, string>>;
export type Vars = Record<string, string | number>;
export type Translate = (key: string, vars?: Vars) => string;

/** Identity. Marks an English string that is passed to `tr(...)` somewhere else. */
export const msg = (key: string): string => key;

/** Replaces {name} placeholders. An unknown placeholder is left as written. */
export function format(template: string, vars?: Vars): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (whole, name: string) => (name in vars ? String(vars[name]) : whole));
}

export function translator(dictionary: Dictionary | undefined): Translate {
  return (key, vars) => format(dictionary?.[key] || key, vars);
}

/** The functional cookie that keeps the chosen language (no personal data). */
export const LANGUAGE_COOKIE = "arogya_lang";

export function parseLanguage(raw: string | null | undefined): Language {
  return raw === "hi" || raw === "mr" ? raw : "en";
}

export function languageCookie(lang: Language): string {
  return `${LANGUAGE_COOKIE}=${lang}; Path=/; Max-Age=31536000; SameSite=Lax`;
}

/** Dates and numbers in the reader's language, with Latin digits so figures match documents. */
export const LOCALE: Record<Language, string> = { en: "en-IN", hi: "hi-IN", mr: "mr-IN-u-nu-latn" };
