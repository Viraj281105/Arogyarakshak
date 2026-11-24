// Command palette model (Wave 3): navigation between real routes only. No search over data, no
// placeholder destinations. Pure, unit-tested in tests/primitives.test.ts. Public paths come from
// nav.ts (PUBLIC_PATHS), the one place to adjust if the public routes move.
import type { Language } from "../shared/i18n/types";
import {
  AUTH_PATHS,
  CASE_PATH,
  MODULE_ORDER,
  PLATFORM_PAGES,
  PUBLIC_PATHS,
  REPORTS_PATH,
  REVIEW_PATH,
  SETTINGS_PATH,
  WORKSPACE_PATH,
  moduleHref,
  platformHref,
} from "./nav";
import { shellCopy } from "./shellCopy";

export interface Command {
  id: string;
  label: string;
  href: string;
  group: "Pages" | "Workspace" | "Checks";
  /** Extra words matched by the filter (English route names stay findable in every language). */
  keywords: string;
}

export function paletteCommands(lang: Language): Command[] {
  const c = shellCopy[lang];
  return [
    { id: "home", label: c.nav.home, href: "/", group: "Pages", keywords: "home landing start" },
    { id: "platform", label: c.nav.platform, href: PUBLIC_PATHS.platform, group: "Pages", keywords: "platform modules overview" },
    ...PLATFORM_PAGES.map((id) => ({
      id: `platform-${id}`,
      label: `${c.nav.platform}: ${id === "kadi" ? c.platformKadi : c.tabs[id]}`,
      href: platformHref(id),
      group: "Pages" as const,
      keywords: `${id} platform`,
    })),
    { id: "how-it-works", label: c.nav.howItWorks, href: PUBLIC_PATHS.howItWorks, group: "Pages", keywords: "how it works steps" },
    { id: "security", label: c.nav.security, href: PUBLIC_PATHS.security, group: "Pages", keywords: "security privacy retention" },
    { id: "about", label: c.nav.about, href: PUBLIC_PATHS.about, group: "Pages", keywords: "about mission" },
    { id: "help", label: c.nav.help, href: PUBLIC_PATHS.help, group: "Pages", keywords: "help faq support" },
    { id: "reviewer", label: c.nav.reviewer, href: REVIEW_PATH, group: "Pages", keywords: "review reviewer clinician doctor" },
    { id: "workspace", label: c.nav.workspace, href: WORKSPACE_PATH, group: "Workspace", keywords: `cases desk my cases ${WORKSPACE_PATH}` },
    { id: "start", label: c.nav.check, href: `${WORKSPACE_PATH}#intake-dropzone`, group: "Workspace", keywords: "start new case upload document check" },
    { id: "case", label: c.nav.caseOverview, href: CASE_PATH, group: "Workspace", keywords: "case overview timeline graph documents insights" },
    { id: "reports", label: c.nav.reports, href: REPORTS_PATH, group: "Workspace", keywords: "reports pdf appeal claim pack download" },
    { id: "settings", label: c.nav.settings, href: SETTINGS_PATH, group: "Workspace", keywords: "settings preferences language theme account password delete" },
    { id: "login", label: c.account.signIn, href: AUTH_PATHS.login, group: "Workspace", keywords: "sign in login account" },
    { id: "register", label: c.account.register, href: AUTH_PATHS.register, group: "Workspace", keywords: "register sign up create account" },
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
