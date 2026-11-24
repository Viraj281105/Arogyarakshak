// Navigation model shared by the header, the drawer, the footer, the command palette and the
// workspace. Pure data and functions (no JSX), unit-tested in tests/shell.test.ts.

export type ModuleTab = "billnyay" | "bimanyay" | "daavisetu" | "schemesetu" | "dawacheck";

/** Order the five checks appear in (tabs, drawer, landing cards). */
export const MODULE_ORDER: readonly ModuleTab[] = ["billnyay", "daavisetu", "bimanyay", "schemesetu", "dawacheck"];

/** Short reference badge per check. Icons live in shell/icons.ts (lucide-react, decision D3). */
export const MODULE_META: Record<ModuleTab, { badge: string }> = {
  billnyay: { badge: "CGHS" },
  daavisetu: { badge: "Pre-Auth" },
  bimanyay: { badge: "IRDAI" },
  schemesetu: { badge: "PMJAY" },
  dawacheck: { badge: "NPPA" },
};

const HASH_PREFIX = "#module-";

/** The case desk (Wave 3: the workspace moved off `/`, which is now the public landing page). */
export const WORKSPACE_PATH = "/app";

/** The open case's overview. The case itself is never in the URL (held in sessionStorage). */
export const CASE_PATH = "/app/case";

/** Per-case reports (appeal PDF, claim PDF, claim pack, appeal verification). */
export const REPORTS_PATH = "/app/case/reports";

/** Preferences, account and case deletion. */
export const SETTINGS_PATH = "/app/settings";

/** The clinical reviewer workspace (Wave 3: it was /clinical-review, which now redirects here). */
export const REVIEW_PATH = "/review";

/** Account pages (ADR-026). */
export const AUTH_PATHS = {
  login: "/login",
  register: "/register",
  forgotPassword: "/forgot-password",
  resetPassword: "/reset-password",
  verify: "/verify",
} as const;

/**
 * Public pages built by the Wave 3 M3 stream. ONE place for their paths: if M3's final routes
 * differ, change them here and the header, drawer, footer and command palette follow.
 */
// Single source of truth for the public routes is M3's publicRoutes.ts (the footer already loads it
// on every route, so importing it here costs nothing extra).
import { PUBLIC_ROUTES } from "../components/public/publicRoutes";
export const PUBLIC_PATHS = PUBLIC_ROUTES;

/** The six platform pages (Kadi is the shared document layer, not a sixth check). */
export const PLATFORM_PAGES = ["kadi", "billnyay", "daavisetu", "bimanyay", "schemesetu", "dawacheck"] as const;
export type PlatformPage = (typeof PLATFORM_PAGES)[number];

export function platformHref(id: PlatformPage): string {
  return `${PUBLIC_PATHS.platform}/${id}`;
}

/** `#module-<id>`: the old workspace hash; the case desk still forwards it to the module page. */
export function moduleHash(id: ModuleTab): string {
  return `${HASH_PREFIX}${id}`;
}

/** `/app/case/<id>`: one check in the workspace, for the open case (or stand-alone without one). */
export function moduleHref(id: ModuleTab): string {
  return `${CASE_PATH}/${id}`;
}

export function isModuleTab(id: string): id is ModuleTab {
  return (MODULE_ORDER as readonly string[]).includes(id);
}

/** The check a `#module-<id>` hash points at, or null. */
export function moduleFromHash(hash: string): ModuleTab | null {
  if (!hash.startsWith(HASH_PREFIX)) return null;
  const id = hash.slice(HASH_PREFIX.length);
  return isModuleTab(id) ? id : null;
}

/** Primary navigation (labels live in shellCopy.nav). */
export const NAV_ITEMS = [
  { key: "platform", href: PUBLIC_PATHS.platform },
  { key: "howItWorks", href: PUBLIC_PATHS.howItWorks },
  { key: "security", href: PUBLIC_PATHS.security },
  { key: "help", href: PUBLIC_PATHS.help },
  { key: "workspace", href: WORKSPACE_PATH },
] as const;

/** Secondary links (drawer and command palette). */
export const SECONDARY_ITEMS = [
  { key: "about", href: PUBLIC_PATHS.about },
  { key: "reviewer", href: REVIEW_PATH },
] as const;

/**
 * Whether a nav href is the current page: the same path or a page below it (`/platform/kadi`
 * under Platform, `/app/case` under the workspace). Hash links are sections, never "the current
 * page"; `/` matches only itself.
 */
export function isActiveHref(href: string, pathname: string): boolean {
  if (href.includes("#")) return false;
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}
