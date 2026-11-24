// Formatting helpers for the workspace (Wave 3 M4). The copy lives in caseCopy, deskCopy,
// overviewCopy, timelineCopy, graphCopy, reportsCopy and settingsCopy (one file per page area).
import type { Language } from "../../shared/i18n/types";

/** Replaces {name} placeholders. */
export function fillCopy(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (m, k: string) => (k in values ? String(values[k]) : m));
}

const LOCALE: Record<Language, string> = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" };

/** Server timestamps are UTC, sometimes without a zone suffix. */
function parseServerDate(value: string): Date | null {
  const iso = /[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatDate(value: string, lang: Language): string {
  const d = parseServerDate(value);
  return d ? d.toLocaleDateString(LOCALE[lang], { day: "numeric", month: "short", year: "numeric" }) : value;
}

export function formatDateTime(value: string, lang: Language): string {
  const d = parseServerDate(value);
  return d ? d.toLocaleString(LOCALE[lang], { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : value;
}

export function formatRupees(amount: number, lang: Language): string {
  return new Intl.NumberFormat(LOCALE[lang], { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(amount);
}

/** First 8 characters of a case id: enough to tell cases apart, and never a token. */
export function shortCaseId(id: string): string {
  return id.replace(/^CASE-/i, "").slice(0, 8);
}

/** "missing_context" keys and summary fields as words ("billing_item" -> "Billing item"). */
export function humanizeKey(key: string): string {
  const s = key.replace(/[_.]+/g, " ").trim();
  return s ? s[0].toUpperCase() + s.slice(1) : key;
}
