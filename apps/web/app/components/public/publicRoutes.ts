// Public-site routes and their footer link labels (Wave 3 M3). The site footer renders on EVERY
// route, so this file is as small as possible (bundle budget: each byte here is paid by /app too).
//
// UNREVIEWED: Hindi and Marathi labels are not written. The pages these links open are English
// only (components/public/publicCopy.ts), so the labels stay English in every UI language until a
// native speaker writes both.

export const PUBLIC_ROUTES = {
  platform: "/platform",
  howItWorks: "/how-it-works",
  security: "/security",
  about: "/about",
  help: "/help",
} as const;
export type PublicRouteKey = keyof typeof PUBLIC_ROUTES;

/** English link labels, in footer order. M4 reuses them for the header nav and command palette. */
export const PUBLIC_ROUTE_LABELS: Record<PublicRouteKey, string> = {
  platform: "Platform",
  howItWorks: "How it works",
  security: "Security & privacy",
  about: "About",
  help: "Help & FAQ",
};

/** [href, label] pairs for the footer. */
export const PUBLIC_FOOTER_LINKS: ReadonlyArray<readonly [string, string]> = (Object.keys(PUBLIC_ROUTES) as PublicRouteKey[]).map(
  (k) => [PUBLIC_ROUTES[k], PUBLIC_ROUTE_LABELS[k]] as const,
);
