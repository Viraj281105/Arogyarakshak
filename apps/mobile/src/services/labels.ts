
import { msg, tr } from '../translations/tr';/**
 * Patient-readable labels for internal status enums (mirrors apps/web/app/lib/labels.ts).
 * Internal enums stay in code; the UI shows these. English-first; Hindi/Marathi clinical
 * wording is pending native-speaker review.
 */
const LABELS: Record<string, string> = {
  PLAUSIBLE: msg('Plausible'),
  INSUFFICIENT_INFORMATION: msg('Insufficient information'),
  POTENTIAL_INCONSISTENCY: msg('Potential inconsistency'),
  CLINICAL_REVIEW_RECOMMENDED: msg('Clinical review recommended'),
  REQUESTED: msg('Review requested — choose a reviewer'),
  ASSIGNED: msg('Reviewer assigned — awaiting acceptance'),
  IN_REVIEW: msg('Under clinical review'),
  COMPLETED: msg('Review completed'),
  DECLINED: msg('Reviewer declined'),
  CANCELLED: msg('Cancelled'),
  FINALIZED: msg('Finalized'),
  SUPERSEDED: msg('Superseded by a newer version'),
  WITHDRAWN: msg('Withdrawn by the reviewer'),
  OPEN: msg('Awaiting a human reading'),
  AWAITING_SECOND_REVIEW: msg('One reading in — a second is required'),
  RESOLVED: msg('Readers agreed'),
  HUMAN_ESCALATION_REQUIRED: msg('Readers disagreed or could not read it'),
  AWAITING_HUMAN_READING: msg('Awaiting human reading'),
  READERS_DISAGREED: msg('Readers disagreed — confirm with pharmacist'),
  READING_NOT_APPLIED: msg('Human reading could not be applied'),
  OCR_UNCERTAIN: msg('Unclear on the document — not yet read by a human'),
  HUMAN_RESOLVED: msg('Human-reviewed reading'),
  MACHINE_EXTRACTED: msg('Machine-extracted'),
  PRESENT: msg('Found in your documents'),
  MISSING: msg('Not found in the text checked'),
  NEEDS_CLINICAL_CONFIRMATION: msg("Needs a doctor's confirmation"),
  CONFIRMED_BY_REVIEWER: msg('Confirmed by a named doctor'),
  REJECTED_BY_REVIEWER: msg('Not confirmed by the doctor'),
  REVIEWER_COULD_NOT_DETERMINE: msg('Doctor could not determine'),
};

export function humanizeEnum(value: string | null | undefined): string {
  if (!value) return '';
  if (LABELS[value]) return tr(LABELS[value]);
  const words = value.replace(/_/g, ' ').toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}
