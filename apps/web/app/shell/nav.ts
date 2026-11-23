// Navigation model shared by the header, the drawer, the footer and the home page's module tabs.
// Pure data and functions (no JSX), unit-tested in tests/shell.test.ts.

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

/** `#module-<id>`: deep link that opens one check on the home page. */
export function moduleHash(id: ModuleTab): string {
  return `${HASH_PREFIX}${id}`;
}

/** The check a `#module-<id>` hash points at, or null. */
export function moduleFromHash(hash: string): ModuleTab | null {
  if (!hash.startsWith(HASH_PREFIX)) return null;
  const id = hash.slice(HASH_PREFIX.length);
  return (MODULE_ORDER as readonly string[]).includes(id) ? (id as ModuleTab) : null;
}

/** Primary navigation (labels live in shellCopy.nav). */
export const NAV_ITEMS = [
  { key: "check", href: "/#intake-dropzone" },
  { key: "modules", href: "/#module-workspace" },
  { key: "reviewer", href: "/clinical-review" },
] as const;

/** Whether a nav href is the current page (hash links are sections, never "the current page"). */
export function isActiveHref(href: string, pathname: string): boolean {
  if (href.includes("#")) return false;
  return href === pathname;
}
