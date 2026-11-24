// Command palette model (Wave 3 M2): navigation between EXISTING routes only. No search over data,
// no placeholder destinations. Pure, unit-tested in tests/primitives.test.ts.
import type { Language } from "../shared/i18n/types";
import { MODULE_ORDER, NAV_ITEMS, REVIEW_PATH, WORKSPACE_PATH, moduleHref } from "./nav";
import { shellCopy } from "./shellCopy";

export interface Command {
  id: string;
  label: string;
  href: string;
  group: "Pages" | "Checks";
  /** Extra words matched by the filter (English route names stay findable in every language). */
  keywords: string;
}

export function paletteCommands(lang: Language): Command[] {
  const c = shellCopy[lang];
  const nav = Object.fromEntries(NAV_ITEMS.map((i) => [i.key, i.href])) as Record<(typeof NAV_ITEMS)[number]["key"], string>;
  return [
    { id: "home", label: c.nav.home, href: "/", group: "Pages", keywords: "home landing start" },
    { id: "check", label: c.nav.check, href: nav.check, group: "Pages", keywords: `upload document workspace case ${WORKSPACE_PATH}` },
    { id: "modules", label: c.nav.modules, href: nav.modules, group: "Pages", keywords: "checks modules workspace" },
    { id: "reviewer", label: c.nav.reviewer, href: REVIEW_PATH, group: "Pages", keywords: "review reviewer clinician doctor" },
    ...MODULE_ORDER.map((id) => ({ id: `module-${id}`, label: c.tabs[id], href: moduleHref(id), group: "Checks" as const, keywords: id })),
  ];
}

/** Case-insensitive match of every query word against label + keywords; empty query keeps all. */
export function filterCommands(commands: readonly Command[], query: string): Command[] {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) return [...commands];
  return commands.filter((cmd) => {
    const hay = `${cmd.label} ${cmd.keywords}`.toLowerCase();
    return words.every((w) => hay.includes(w));
  });
}

/** Ctrl+K (Windows/Linux) or Cmd+K (macOS), without Shift/Alt. */
export function isPaletteShortcut(e: { key: string; ctrlKey: boolean; metaKey: boolean; shiftKey: boolean; altKey: boolean }): boolean {
  return e.key.toLowerCase() === "k" && (e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey;
}
