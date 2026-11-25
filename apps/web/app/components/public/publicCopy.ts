// Public-site copy (Wave 3 M3). English (copy/en.ts, copy/modules.ts) is the source; Hindi and
// Marathi are the same structure with every text run through the UI dictionaries.
//
// UNREVIEWED: the Hindi and Marathi text is MACHINE TRANSLATION (Claude) and NEEDS
// NATIVE-SPEAKER QA (apps/web/AGENTS.md, docs/localization.md). Pages in those languages say so
// (PublicLanguageNotice).
//
// Server-only in practice: client components must receive strings as props and never import this
// file (tests/public_site.test.ts enforces it), so the copy stays out of every JS bundle.
import { translator, type Translate } from "../../i18n/format";
import { loadDictionary } from "../../i18n/load";
import { EVIDENCE_STATES } from "../ui/evidence";
import type { Language } from "../../shared/i18n/types";
import { PUBLIC_EN } from "./copy/en";
import type { PublicCopy } from "./copy/types";

export type { PublicCopy } from "./copy/types";

/** Fields that hold identifiers, addresses or code references. */
const IDENTIFIER_FIELDS: ReadonlySet<string> = new Set(["id", "ids", "href", "state", "topic", "source", "location", "native", "translation", "siteName"]);
const EVIDENCE_IDS: ReadonlySet<string> = new Set(EVIDENCE_STATES);

/**
 * True when `value` under `key` is an identifier, never translated. Only plain strings and lists
 * count: a section that happens to share a field's name is still text. `evidence` is used both for
 * evidence-state ids and for headings and sections, so there the value itself decides.
 */
export function isIdentifier(key: string, value: unknown): boolean {
  const list = Array.isArray(value) ? value : [value];
  if (!list.every((item) => typeof item === "string")) return false;
  if (key === "evidence") return list.every((item) => EVIDENCE_IDS.has(item as string));
  return IDENTIFIER_FIELDS.has(key);
}

/** A copy of `value` with every text string translated. */
export function translateCopy<T>(value: T, tr: Translate, key = ""): T {
  if (isIdentifier(key, value)) return value;
  if (typeof value === "string") return tr(value) as T;
  if (Array.isArray(value)) return value.map((item) => translateCopy(item, tr, key)) as T;
  if (value && typeof value === "object")
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, translateCopy(v, tr, k)])) as T;
  return value;
}

/** The English source copy. */
export function publicCopy(): PublicCopy {
  return PUBLIC_EN;
}

/** The copy a page renders in `lang`. */
export async function localisedPublicCopy(lang: Language): Promise<PublicCopy> {
  if (lang === "en") return PUBLIC_EN;
  const copy = translateCopy(PUBLIC_EN, translator(await loadDictionary(lang)));
  return { ...copy, translation: "machine" };
}

/** "<page> · ArogyaRakshak" for every public page except the landing page. */
export function pageTitle(title: string): string {
  return `${title} · ${PUBLIC_EN.siteName}`;
}
