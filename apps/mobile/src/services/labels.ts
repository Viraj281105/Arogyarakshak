/**
 * Patient-readable labels for internal status enums (mirrors apps/web/app/lib/labels.ts).
 * Internal enums stay in code; the UI shows these. English-first; Hindi/Marathi clinical
 * wording is pending native-speaker review.
 */
const LABELS: Record<string, string> = {
  PLAUSIBLE: 'Plausible',
  INSUFFICIENT_INFORMATION: 'Insufficient information',
  POTENTIAL_INCONSISTENCY: 'Potential inconsistency',
  CLINICAL_REVIEW_RECOMMENDED: 'Clinical review recommended',
  REQUESTED: 'Review requested — choose a reviewer',
  ASSIGNED: 'Reviewer assigned — awaiting acceptance',
  IN_REVIEW: 'Under clinical review',
  COMPLETED: 'Review completed',
  DECLINED: 'Reviewer declined',
  CANCELLED: 'Cancelled',
  FINALIZED: 'Finalized',
  SUPERSEDED: 'Superseded by a newer version',
  WITHDRAWN: 'Withdrawn by the reviewer',
  OPEN: 'Awaiting a human reading',
  AWAITING_SECOND_REVIEW: 'One reading in — a second is required',
  RESOLVED: 'Readers agreed',
  HUMAN_ESCALATION_REQUIRED: 'Readers disagreed or could not read it',
  AWAITING_HUMAN_READING: 'Awaiting human reading',
  READERS_DISAGREED: 'Readers disagreed — confirm with pharmacist',
  READING_NOT_APPLIED: 'Human reading could not be applied',
  OCR_UNCERTAIN: 'Unclear on the document — not yet read by a human',
  HUMAN_RESOLVED: 'Human-reviewed reading',
  MACHINE_EXTRACTED: 'Machine-extracted',
  PRESENT: 'Found in your documents',
  MISSING: 'Not found in the text checked',
  NEEDS_CLINICAL_CONFIRMATION: "Needs a doctor's confirmation",
  CONFIRMED_BY_REVIEWER: 'Confirmed by a named doctor',
  REJECTED_BY_REVIEWER: 'Not confirmed by the doctor',
  REVIEWER_COULD_NOT_DETERMINE: 'Doctor could not determine',
};

export function humanizeEnum(value: string | null | undefined): string {
  if (!value) return '';
  if (LABELS[value]) return LABELS[value];
  const words = value.replace(/_/g, ' ').toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}
