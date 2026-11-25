// Server Components only (reads the request's cookies, so the page renders per request).
import { cookies } from "next/headers";
import type { Language } from "../shared/i18n/types";
import { LANGUAGE_COOKIE, parseLanguage, translator, type Translate } from "./format";
import { loadDictionary } from "./load";

export async function requestLanguage(): Promise<Language> {
  return parseLanguage((await cookies()).get(LANGUAGE_COOKIE)?.value);
}

/** The request's language and its translator. */
export async function serverT(): Promise<{ lang: Language; tr: Translate }> {
  const lang = await requestLanguage();
  return { lang, tr: translator(await loadDictionary(lang)) };
}
