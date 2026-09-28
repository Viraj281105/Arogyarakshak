/**
 * DawaCheck price-check presentation (shared by the manual check and the case panel).
 *
 * NPPA ceilings are per tablet/capsule/vial. The server resolves every billed amount to a
 * per-unit price or refuses (`comparison_status: "CANNOT_COMPARE"`); this module only turns
 * that decision into words. It never computes a percentage itself and never shows
 * "within ceiling" for a comparison that was not made.
 */

export type PriceBasis = "PER_UNIT" | "PER_STRIP" | "PER_PACK" | "LINE_TOTAL" | "UNKNOWN";

export interface PriceCheck {
  active_ingredient: string;
  mrp: number;
  nppa_ceiling_price: number;
  is_overcharged: boolean | null;
  deviation_percentage: number | null;
  reference_entry_count: number;
  // Present on servers with price-basis support; absent fields are treated as unknown.
  comparison_status?: "COMPARED" | "CANNOT_COMPARE";
  price_basis?: PriceBasis;
  price_basis_label?: string;
  basis_source?: string;
  basis_evidence?: string | null;
  billed_unit_price?: number | null;
  unit_label?: string;
  comparison_note?: string | null;
  match_method?: string;
}

export interface PriceCheckView {
  verdict: "above" | "within" | "cannot_compare";
  badge: string;
  tone: "danger" | "success" | "warning";
  /** "₹33.00 billed per strip of 15 → ₹2.20 per tablet" */
  billed: string;
  /** "NPPA ceiling ₹2.30 per tablet" */
  ceiling: string;
  /** Where the basis came from, when it came from the document or a default. */
  basisNote: string | null;
  /** Why no comparison was made. */
  reason: string | null;
}

const rupees = (n: number) => `₹${n.toFixed(2)}`;

const BASIS_SOURCE_NOTE: Record<string, string> = {
  DOCUMENT_LINE: "Price basis read from the bill line",
  DOCUMENT_HEADER: "Price basis read from the document's rate column",
  DECLARED: "Price basis as you entered it",
  API_DEFAULT: "Treated as a price per unit (no basis was given)",
};

export function describePriceCheck(b: PriceCheck): PriceCheckView {
  const unit = b.unit_label || "unit";
  const ceiling = `NPPA ceiling ${rupees(b.nppa_ceiling_price)} per ${unit}`;
  const basisLabel = b.price_basis_label || "basis not stated";
  const compared = b.comparison_status === "COMPARED" && typeof b.billed_unit_price === "number" && typeof b.is_overcharged === "boolean";

  const sourceNote = b.basis_source ? BASIS_SOURCE_NOTE[b.basis_source] ?? null : null;
  const basisNote = sourceNote ? (b.basis_evidence ? `${sourceNote}: “${b.basis_evidence}”` : sourceNote) : null;

  if (!compared) {
    return {
      verdict: "cannot_compare",
      badge: "Cannot compare reliably",
      tone: "warning",
      billed: `${rupees(b.mrp)} billed (${basisLabel})`,
      ceiling,
      basisNote,
      reason:
        b.comparison_note ||
        "The price per unit could not be established, so this amount was not compared with the per-unit ceiling.",
    };
  }

  const unitPrice = b.billed_unit_price as number;
  const billed =
    b.price_basis === "PER_UNIT"
      ? `${rupees(unitPrice)} billed per ${unit}`
      : `${rupees(b.mrp)} billed ${basisLabel} → ${rupees(unitPrice)} per ${unit}`;

  if (b.is_overcharged) {
    const pct = typeof b.deviation_percentage === "number" ? ` (+${b.deviation_percentage}%)` : "";
    return { verdict: "above", badge: `Above ceiling${pct}`, tone: "danger", billed, ceiling, basisNote, reason: null };
  }
  return { verdict: "within", badge: "Within ceiling", tone: "success", billed, ceiling, basisNote, reason: null };
}
