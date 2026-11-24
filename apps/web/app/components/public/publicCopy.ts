// Public-site copy (Wave 3 M3), one module per language.
//
// UNREVIEWED: Hindi and Marathi public-site copy has NOT been written. Writing it needs a native
// speaker (apps/web/AGENTS.md: never ship Hindi or Marathi copy without native-speaker QA), so the
// `hi` and `mr` entries are explicit stubs: they reuse the English text and are marked
// `translation: "pending"`. No machine-written Hindi or Marathi is presented as reviewed. Public
// pages are Server Components and render English; when the visitor picks हिंदी or मराठी the
// client-side PublicLanguageNotice says the page is English only for now.
//
// Server-only in practice: client components must receive strings as props and never import this
// file (tests/public_site.test.ts enforces it), so the copy stays out of every JS bundle.
import type { Language } from "../../shared/i18n/types";
import { PUBLIC_EN } from "./copy/en";
import type { PublicCopy } from "./copy/types";

export type { PublicCopy } from "./copy/types";

export const PUBLIC_COPY: Record<Language, PublicCopy> = {
  en: PUBLIC_EN,
  // UNREVIEWED stub: English text until a native speaker writes and reviews the Hindi copy.
  hi: { ...PUBLIC_EN, translation: "pending" },
  // UNREVIEWED stub: English text until a native speaker writes and reviews the Marathi copy.
  mr: { ...PUBLIC_EN, translation: "pending" },
};

/** The copy pages render. English until reviewed translations exist. */
export function publicCopy(lang: Language = "en"): PublicCopy {
  return PUBLIC_COPY[lang];
}

/** "<page> · ArogyaRakshak" for every public page except the landing page. */
export function pageTitle(title: string): string {
  return `${title} · ${PUBLIC_EN.siteName}`;
}
