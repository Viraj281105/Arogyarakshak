// Kept apart from ./format so that file stays free of dynamic imports (the mobile tests
// type-check web modules that use `msg`).
import type { Language } from "../shared/i18n/types";
import type { Dictionary } from "./format";

/** Loads one language's dictionary as its own chunk, so English visitors download none. */
export async function loadDictionary(lang: Language): Promise<Dictionary | undefined> {
  if (lang === "hi") return (await import("./locales/hi")).default;
  if (lang === "mr") return (await import("./locales/mr")).default;
  return undefined;
}
