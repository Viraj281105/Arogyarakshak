// Public-site routes (Wave 3 M3) and their short link labels. Pure data, no JSX, small on purpose:
// the client footer imports it, so it must not pull the page copy (copy/en.ts) into the JS bundle.
// M4 adds these routes to the header nav and the command palette from this one list.
import type { Language } from "../../shared/i18n/types";
import { PUBLIC_ROUTES } from "./publicRoutes";

export { PUBLIC_ROUTES, PUBLIC_ROUTE_LABELS, type PublicRouteKey } from "./publicRoutes";

/** Kadi first (the shared document layer), then the five checks in MODULE_ORDER. */
export const PUBLIC_MODULE_IDS = ["kadi", "billnyay", "daavisetu", "bimanyay", "schemesetu", "dawacheck"] as const;
export type PublicModuleId = (typeof PUBLIC_MODULE_IDS)[number];

/** `/platform/<id>`: one statically generated page per capability. */
export function platformModuleHref(id: PublicModuleId): string {
  return `${PUBLIC_ROUTES.platform}/${id}`;
}

/** Every public route this stream adds, in footer order (the exact list handed to M4). */
export function allPublicPaths(): string[] {
  return [
    PUBLIC_ROUTES.platform,
    ...PUBLIC_MODULE_IDS.map(platformModuleHref),
    PUBLIC_ROUTES.howItWorks,
    PUBLIC_ROUTES.security,
    PUBLIC_ROUTES.about,
    PUBLIC_ROUTES.help,
  ];
}

/**
 * Shown on public pages when the UI language is Hindi or Marathi: the page text itself is English
 * only until a native speaker writes and reviews it. NEEDS NATIVE-SPEAKER QA (engineering-written).
 */
export const PUBLIC_LANGUAGE_NOTICE: Record<Exclude<Language, "en">, string> = {
  hi: "यह पृष्ठ अभी केवल अंग्रेज़ी में है। हिंदी पाठ किसी मूल भाषी की समीक्षा के बाद जोड़ा जाएगा।",
  mr: "हे पृष्ठ सध्या फक्त इंग्रजीत आहे. मराठी मजकूर मूळ भाषकाच्या पुनरावलोकनानंतर जोडला जाईल.",
};
