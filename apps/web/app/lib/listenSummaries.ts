/**
 * Builds the read-aloud / simple-language summaries from STRUCTURED result fields only.
 * Server free text (which is mostly English) is never spoken, so the language heard always
 * matches the selected UI language and nothing unreviewed is read out. Pure functions.
 */

import type { Language } from "../translations";
import { listenCopy, type Register } from "./listenCopy";

export type Summary = Register;

export const fill = (template: string, values: Record<string, string | number>): string =>
  template.replace(/\{(\w+)\}/g, (m, k: string) => (k in values ? String(values[k]) : m));

const join = (parts: Register[]): Summary => ({
  standard: parts.map((p) => p.standard).join(" "),
  simple: parts.map((p) => p.simple).join(" "),
});

const apply = (r: Register, values: Record<string, string | number>): Register => ({
  standard: fill(r.standard, values),
  simple: fill(r.simple, values),
});

const LOCALE: Record<Language, string> = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" };

/** "2026-11-12" -> "12 November 2026" in the UI language; unparseable input is returned as given. */
export function formatSpokenDate(value: string, lang: Language): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (!m) return value;
  const d = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  if (Number.isNaN(d.getTime())) return value;
  try {
    return new Intl.DateTimeFormat(LOCALE[lang], { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(d);
  } catch {
    return value;
  }
}

const money = (n: number) => n.toFixed(2);

// --- Deadlines (BimaNyay grievance timeline) -----------------------------------------------------

export interface DeadlineEventInput {
  tier: string;
  status: string;
  deadline_date?: string | null;
}

export function buildDeadlineSummary(events: readonly DeadlineEventInput[], lang: Language): Summary {
  const c = listenCopy[lang].deadline;
  const parts: Register[] = [c.intro];
  events.forEach((e, i) => {
    const tier = (c.tiers as Record<string, Register>)[e.tier] ?? apply(c.tierFallback, { n: i + 1 });
    const status = (c.status as Record<string, Register>)[e.status] ?? c.statusFallback;
    // The tier/status text of one register is used within the same register's frame.
    const date = e.deadline_date ? formatSpokenDate(e.deadline_date, lang) : null;
    const frame = date ? c.event : c.eventNoDate;
    parts.push({
      standard: fill(frame.standard, { tier: tier.standard, status: status.standard, date: date ?? "" }),
      simple: fill(frame.simple, { tier: tier.simple, status: status.simple, date: date ?? "" }),
    });
  });
  return join(parts);
}

// --- Readiness checklist (DaaviSetu) --------------------------------------------------------------

export interface ReadinessItemInput {
  status: string;
}

export function buildReadinessSummary(items: readonly ReadinessItemInput[], lang: Language): Summary {
  const c = listenCopy[lang].readiness;
  const count = (...statuses: string[]) => items.filter((i) => statuses.includes(i.status)).length;
  const found = count("PRESENT", "CONFIRMED_BY_REVIEWER");
  const missing = count("MISSING");
  const needsDoctor = count("NEEDS_CLINICAL_CONFIRMATION");
  const notConfirmed = count("REJECTED_BY_REVIEWER", "REVIEWER_COULD_NOT_DETERMINE");
  const parts: Register[] = [apply(c.headline, { found, total: items.length })];
  if (missing > 0) parts.push(apply(c.missing, { n: missing }));
  if (needsDoctor > 0) parts.push(apply(c.needsDoctor, { n: needsDoctor }));
  if (notConfirmed > 0) parts.push(apply(c.notConfirmed, { n: notConfirmed }));
  if (missing + needsDoctor + notConfirmed === 0 && items.length > 0) parts.push(c.allPresent);
  parts.push(c.scope);
  return join(parts);
}

// --- Medicine price comparison (DawaCheck) --------------------------------------------------------

export interface MedicineInput {
  brandName: string;
  activeIngredient: string;
  verdict: "above" | "within" | "cannot_compare";
  billedUnitPrice?: number | null;
  ceilingUnitPrice?: number | null;
  genericAvailable?: boolean;
}

export function buildMedicineSummary(m: MedicineInput, lang: Language): Summary {
  const c = listenCopy[lang].medicine;
  const parts: Register[] = [apply(c.intro, { brand: m.brandName, ingredient: m.activeIngredient })];
  const numbers =
    typeof m.billedUnitPrice === "number" && typeof m.ceilingUnitPrice === "number"
      ? { billed: money(m.billedUnitPrice), ceiling: money(m.ceilingUnitPrice) }
      : null;
  // A verdict is only spoken when the figures behind it are present; otherwise say no comparison was made.
  if (m.verdict === "above" && numbers) parts.push(apply(c.above, numbers));
  else if (m.verdict === "within" && numbers) parts.push(apply(c.within, numbers));
  else parts.push(c.cannotCompare);
  if (m.genericAvailable) parts.push(c.genericListed);
  return join(parts);
}

// --- Appeal summary (BimaNyay) -------------------------------------------------------------------

export interface AppealInput {
  isWrongfulDenial: boolean;
  violationCount: number;
  /** 0..1; only spoken when `heuristic` is true so it is always labelled as a rule-based estimate. */
  reversalScore?: number | null;
  heuristic: boolean;
}

export function buildAppealSummary(a: AppealInput, lang: Language): Summary {
  const c = listenCopy[lang].appeal;
  const parts: Register[] = [a.isWrongfulDenial ? c.wrongful : c.notWrongful];
  parts.push(a.violationCount > 0 ? apply(c.violations, { n: a.violationCount }) : c.noViolations);
  parts.push(c.drafts);
  if (a.heuristic && typeof a.reversalScore === "number") {
    parts.push(apply(c.estimate, { pct: Math.round(a.reversalScore * 100) }));
  }
  parts.push(c.checkBeforeSending);
  return join(parts);
}
