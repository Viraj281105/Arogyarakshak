/**
 * Patient- and reviewer-readable labels for internal status enums.
 *
 * Internal enums stay in code and in API payloads; the UI shows these labels instead
 * (e.g. POTENTIAL_INCONSISTENCY -> "Potential inconsistency"). English-first; Hindi/Marathi
 * versions of clinical wording are pending native-speaker review.
 */

import { msg } from "../i18n/format";
const LABELS: Record<string, string> = {
  // Plausibility (BillNyay)
  PLAUSIBLE: msg("Plausible"),
  INSUFFICIENT_INFORMATION: msg("Insufficient information"),
  POTENTIAL_INCONSISTENCY: msg("Potential inconsistency"),
  CLINICAL_REVIEW_RECOMMENDED: msg("Clinical review recommended"),
  CLINICAL_REVIEW_REQUIRED: msg("Clinical review recommended"),
  NOT_REQUIRED: msg("No clinical review needed"),
  FULL: msg("All billed items assessed"),
  PARTIAL: msg("Some items not assessed"),
  NONE: msg("Nothing could be assessed"),

  // Review lifecycle
  REQUESTED: msg("Review requested — choose a reviewer"),
  ASSIGNED: msg("Reviewer assigned — awaiting acceptance"),
  IN_REVIEW: msg("Under clinical review"),
  COMPLETED: msg("Review completed"),
  DECLINED: msg("Reviewer declined"),
  CANCELLED: msg("Cancelled"),

  // Statement lifecycle
  DRAFT: msg("Draft (private to the reviewer)"),
  UNDER_REVIEW: msg("Locked for finalization"),
  FINALIZED: msg("Finalized"),
  SUPERSEDED: msg("Superseded by a newer version"),
  WITHDRAWN: msg("Withdrawn by the reviewer"),

  // Fact confirmation (DaaviSetu)
  PENDING: msg("Awaiting the reviewer"),
  CONFIRMED: msg("Confirmed by the reviewer"),
  REJECTED: msg("Not confirmed by the reviewer"),
  CANNOT_DETERMINE: msg("Reviewer could not determine"),

  // Readiness items
  PRESENT: msg("Found in your documents"),
  MISSING: msg("Not found in the text checked"),
  NEEDS_CLINICAL_CONFIRMATION: msg("Needs a doctor's confirmation"),
  CONFIRMED_BY_REVIEWER: msg("Confirmed by a named doctor"),
  REJECTED_BY_REVIEWER: msg("Not confirmed by the doctor"),
  REVIEWER_COULD_NOT_DETERMINE: msg("Doctor could not determine"),

  // Transcription tasks
  OPEN: msg("Awaiting a human reading"),
  AWAITING_SECOND_REVIEW: msg("One reading in — a second independent reading is required"),
  RESOLVED: msg("Readers agreed"),
  HUMAN_ESCALATION_REQUIRED: msg("Readers disagreed or could not read it"),

  // Medicine trust (DawaCheck)
  AWAITING_HUMAN_READING: msg("Awaiting human reading"),
  READERS_DISAGREED: msg("Readers disagreed — confirm with pharmacist"),
  READING_NOT_APPLIED: msg("Human reading could not be applied"),
  OCR_UNCERTAIN: msg("Unclear on the document — not yet read by a human"),
  HUMAN_RESOLVED: msg("Human-reviewed reading"),
  MACHINE_EXTRACTED: msg("Machine-extracted"),
  AMBIGUOUS: msg("Unclear reading could match more than one medicine"),
  POSSIBLE_MATCH: msg("Unclear reading only resembles this name"),
  OVER_CAP: msg("Unclear, but over the automatic reading limit"),
  UNGROUNDED: msg("Name not found in the clearly read text"),

  // Field types / risk
  MEDICINE_NAME: msg("Medicine name"),
  STRENGTH: msg("Strength"),
  FREQUENCY: msg("Frequency"),
  ROUTE: msg("Route"),
  DURATION: msg("Duration"),
  UNCLASSIFIED: msg("Possibly medication-related text"),
  HIGH: msg("High risk"),
  STANDARD: msg("Standard"),

  // Safety rules
  APPROVED: msg("Approved — not yet active"),
  ACTIVE: msg("Active"),
  RETIRED: msg("Retired"),
  URGENT: msg("Urgent"),
  ADVISORY: msg("Advisory"),
};

/** Sentence-case fallback so an enum the table does not know still reads as words. */
export function humanizeEnum(value: string | null | undefined): string {
  if (!value) return "";
  if (LABELS[value]) return LABELS[value];
  const words = value.replace(/_/g, " ").toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** Readable local date-time; the raw value is kept for a title attribute. */
export function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "";
  // Server timestamps are UTC without a zone suffix.
  const iso = /[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export type Tone = "machine" | "human-reviewed" | "human-authored" | "demo" | "self-declared" | "verified" | "warning" | "danger" | "neutral" | "success";

export const TONE_CLASS: Record<Tone, string> = {
  machine: "badge badge-machine",
  "human-reviewed": "badge badge-human-reviewed",
  "human-authored": "badge badge-human-authored",
  demo: "badge badge-demo",
  "self-declared": "badge badge-self-declared",
  verified: "badge badge-success",
  success: "badge badge-success",
  warning: "badge badge-warning",
  danger: "badge badge-danger",
  neutral: "badge badge-info",
};

/**
 * Verification tone. Only EXTERNALLY_VERIFIED (a real registry check — none exists in this
 * build) may ever look like "verified"; self-declared and demo verification are visibly
 * different from each other and from it.
 */
export function verificationTone(status: string | null | undefined): Tone {
  switch (status) {
    case "EXTERNALLY_VERIFIED":
      return "verified";
    case "DEMO_VERIFIED":
      return "demo";
    case "SELF_DECLARED":
      return "self-declared";
    default:
      return "warning";
  }
}
