/**
 * Patient- and reviewer-readable labels for internal status enums.
 *
 * Internal enums stay in code and in API payloads; the UI shows these labels instead
 * (e.g. POTENTIAL_INCONSISTENCY -> "Potential inconsistency"). English-first; Hindi/Marathi
 * versions of clinical wording are pending native-speaker review.
 */

const LABELS: Record<string, string> = {
  // Plausibility (BillNyay)
  PLAUSIBLE: "Plausible",
  INSUFFICIENT_INFORMATION: "Insufficient information",
  POTENTIAL_INCONSISTENCY: "Potential inconsistency",
  CLINICAL_REVIEW_RECOMMENDED: "Clinical review recommended",
  CLINICAL_REVIEW_REQUIRED: "Clinical review recommended",
  NOT_REQUIRED: "No clinical review needed",
  FULL: "All billed items assessed",
  PARTIAL: "Some items not assessed",
  NONE: "Nothing could be assessed",

  // Review lifecycle
  REQUESTED: "Review requested — choose a reviewer",
  ASSIGNED: "Reviewer assigned — awaiting acceptance",
  IN_REVIEW: "Under clinical review",
  COMPLETED: "Review completed",
  DECLINED: "Reviewer declined",
  CANCELLED: "Cancelled",

  // Statement lifecycle
  DRAFT: "Draft (private to the reviewer)",
  UNDER_REVIEW: "Locked for finalization",
  FINALIZED: "Finalized",
  SUPERSEDED: "Superseded by a newer version",
  WITHDRAWN: "Withdrawn by the reviewer",

  // Fact confirmation (DaaviSetu)
  PENDING: "Awaiting the reviewer",
  CONFIRMED: "Confirmed by the reviewer",
  REJECTED: "Not confirmed by the reviewer",
  CANNOT_DETERMINE: "Reviewer could not determine",

  // Readiness items
  PRESENT: "Found in your documents",
  MISSING: "Not found in the text checked",
  NEEDS_CLINICAL_CONFIRMATION: "Needs a doctor's confirmation",
  CONFIRMED_BY_REVIEWER: "Confirmed by a named doctor",
  REJECTED_BY_REVIEWER: "Not confirmed by the doctor",
  REVIEWER_COULD_NOT_DETERMINE: "Doctor could not determine",

  // Transcription tasks
  OPEN: "Awaiting a human reading",
  AWAITING_SECOND_REVIEW: "One reading in — a second independent reading is required",
  RESOLVED: "Readers agreed",
  HUMAN_ESCALATION_REQUIRED: "Readers disagreed or could not read it",

  // Medicine trust (DawaCheck)
  AWAITING_HUMAN_READING: "Awaiting human reading",
  READERS_DISAGREED: "Readers disagreed — confirm with pharmacist",
  READING_NOT_APPLIED: "Human reading could not be applied",
  OCR_UNCERTAIN: "Unclear on the document — not yet read by a human",
  HUMAN_RESOLVED: "Human-reviewed reading",
  MACHINE_EXTRACTED: "Machine-extracted",
  AMBIGUOUS: "Unclear reading could match more than one medicine",
  POSSIBLE_MATCH: "Unclear reading only resembles this name",
  OVER_CAP: "Unclear, but over the automatic reading limit",
  UNGROUNDED: "Name not found in the clearly read text",

  // Field types / risk
  MEDICINE_NAME: "Medicine name",
  STRENGTH: "Strength",
  FREQUENCY: "Frequency",
  ROUTE: "Route",
  DURATION: "Duration",
  UNCLASSIFIED: "Possibly medication-related text",
  HIGH: "High risk",
  STANDARD: "Standard",

  // Safety rules
  APPROVED: "Approved — not yet active",
  ACTIVE: "Active",
  RETIRED: "Retired",
  URGENT: "Urgent",
  ADVISORY: "Advisory",
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
