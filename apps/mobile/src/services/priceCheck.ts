/**
 * DawaCheck price-check presentation (mobile twin of apps/web/app/lib/dawacheck.ts).
 *
 * NPPA ceilings are per tablet/capsule/vial. The server resolves every billed amount to a
 * per-unit price or refuses (`comparison_status: "CANNOT_COMPARE"`); this only turns that
 * decision into words. It never computes a percentage and never shows "within ceiling" for
 * a comparison that was not made — a payload without price-basis fields counts as not compared.
 */

export type PriceBasis = 'PER_UNIT' | 'PER_STRIP' | 'PER_PACK' | 'LINE_TOTAL' | 'UNKNOWN';

export interface PriceCheck {
  active_ingredient: string;
  mrp: number;
  nppa_ceiling_price: number;
  is_overcharged: boolean | null;
  deviation_percentage: number | null;
  comparison_status?: 'COMPARED' | 'CANNOT_COMPARE';
  price_basis?: PriceBasis;
  price_basis_label?: string;
  basis_source?: string;
  basis_evidence?: string | null;
  billed_unit_price?: number | null;
  unit_label?: string;
  comparison_note?: string | null;
}

export interface PriceCheckView {
  verdict: 'above' | 'within' | 'cannot_compare';
  badge: string;
  variant: 'danger' | 'success' | 'warning';
  billed: string;
  ceiling: string;
  basisNote: string | null;
  reason: string | null;
}

const rupees = (n: number) => `₹${n.toFixed(2)}`;

const BASIS_SOURCE_NOTE: Record<string, string> = {
  DOCUMENT_LINE: 'Price basis read from the bill line',
  DOCUMENT_HEADER: "Price basis read from the document's rate column",
  DECLARED: 'Price basis as you entered it',
  API_DEFAULT: 'Treated as a price per unit (no basis was given)',
};

export function describePriceCheck(b: PriceCheck): PriceCheckView {
  const unit = b.unit_label || 'unit';
  const ceiling = `NPPA ceiling ${rupees(b.nppa_ceiling_price)} per ${unit}`;
  const basisLabel = b.price_basis_label || 'basis not stated';
  const compared =
    b.comparison_status === 'COMPARED' && typeof b.billed_unit_price === 'number' && typeof b.is_overcharged === 'boolean';
  const sourceNote = b.basis_source ? BASIS_SOURCE_NOTE[b.basis_source] ?? null : null;
  const basisNote = sourceNote ? (b.basis_evidence ? `${sourceNote}: “${b.basis_evidence}”` : sourceNote) : null;

  if (!compared) {
    return {
      verdict: 'cannot_compare',
      badge: 'Cannot compare reliably',
      variant: 'warning',
      billed: `${rupees(b.mrp)} billed (${basisLabel})`,
      ceiling,
      basisNote,
      reason:
        b.comparison_note ||
        'The price per unit could not be established, so this amount was not compared with the per-unit ceiling.',
    };
  }
  const unitPrice = b.billed_unit_price as number;
  const billed =
    b.price_basis === 'PER_UNIT'
      ? `${rupees(unitPrice)} billed per ${unit}`
      : `${rupees(b.mrp)} billed ${basisLabel} → ${rupees(unitPrice)} per ${unit}`;
  if (b.is_overcharged) {
    const pct = typeof b.deviation_percentage === 'number' ? ` (+${b.deviation_percentage}%)` : '';
    return { verdict: 'above', badge: `Above ceiling${pct}`, variant: 'danger', billed, ceiling, basisNote, reason: null };
  }
  return { verdict: 'within', badge: 'Within ceiling', variant: 'success', billed, ceiling, basisNote, reason: null };
}

/** What the amount the person paid buys — chosen explicitly, never assumed. */
export const BASIS_OPTIONS: { value: PriceBasis; label: string; needs: 'none' | 'pack' | 'quantity' }[] = [
  { value: 'PER_UNIT', label: 'One tablet/capsule/vial', needs: 'none' },
  { value: 'PER_STRIP', label: 'One strip', needs: 'pack' },
  { value: 'PER_PACK', label: 'One pack/box', needs: 'pack' },
  { value: 'LINE_TOTAL', label: 'Several units', needs: 'quantity' },
];

/** Builds the manual-check request, or an error message when the input is incomplete. */
export function buildBenchmarkRequest(
  brand: string,
  amount: string,
  basis: PriceBasis | null,
  count: string
):
  | { ok: true; body: { brand_name: string; mrp: number; price_basis: PriceBasis; units_per_pack?: number; quantity?: number } }
  | { ok: false; error: string } {
  const name = brand.trim();
  const mrp = parseFloat(amount);
  if (!name) return { ok: false, error: 'Please enter a medicine or brand name.' };
  if (isNaN(mrp) || mrp <= 0) return { ok: false, error: 'Please enter the amount paid (greater than 0).' };
  const option = BASIS_OPTIONS.find((o) => o.value === basis);
  if (!option || !basis) return { ok: false, error: 'Please choose what the amount paid for (one tablet, a strip, a pack…).' };
  if (option.needs === 'none') return { ok: true, body: { brand_name: name, mrp, price_basis: basis } };
  const n = Number(count);
  if (!Number.isInteger(n) || n <= 0) {
    return {
      ok: false,
      error: option.needs === 'pack' ? 'Please enter how many units are in the strip/pack.' : 'Please enter how many units the amount covers.',
    };
  }
  return {
    ok: true,
    body: option.needs === 'pack' ? { brand_name: name, mrp, price_basis: basis, units_per_pack: n } : { brand_name: name, mrp, price_basis: basis, quantity: n },
  };
}
