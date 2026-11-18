// Navigation model shared by the header, the drawer, the footer and the home page's module tabs.
// Pure data and functions (no JSX), unit-tested in tests/shell.test.ts.

export type ModuleTab = "billnyay" | "bimanyay" | "daavisetu" | "schemesetu" | "dawacheck";

/** Order the five checks appear in (tabs, drawer, landing cards). */
export const MODULE_ORDER: readonly ModuleTab[] = ["billnyay", "daavisetu", "bimanyay", "schemesetu", "dawacheck"];

/** Short reference badge and a 24x24 stroke-icon path per check. */
export const MODULE_META: Record<ModuleTab, { badge: string; icon: string }> = {
  billnyay: { badge: "CGHS", icon: "M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6M9 16h3" },
  daavisetu: { badge: "Pre-Auth", icon: "M8 4h8v3H8zM6 6H5v15h14V6h-1M9 12h6M9 16h4" },
  bimanyay: { badge: "IRDAI", icon: "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM9 12l2 2 4-4" },
  schemesetu: { badge: "PMJAY", icon: "M3 10l9-6 9 6M5 10v9M19 10v9M9 10v9M15 10v9M3 21h18" },
  dawacheck: { badge: "NPPA", icon: "M10.5 4.5a5 5 0 0 1 7 7l-6 6a5 5 0 0 1-7-7zM8 9l7 7" },
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
