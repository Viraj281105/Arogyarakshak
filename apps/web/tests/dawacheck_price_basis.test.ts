import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describePriceCheck, PriceCheck } from '../app/lib/dawacheck';

const read = (...p: string[]) => readFileSync(join(process.cwd(), ...p), 'utf-8');

const base: PriceCheck = {
  active_ingredient: 'Paracetamol 650mg',
  mrp: 33,
  nppa_ceiling_price: 2.3,
  is_overcharged: null,
  deviation_percentage: null,
  reference_entry_count: 7,
  unit_label: 'tablet',
};

describe('DawaCheck price basis (web)', () => {
  it('shows a converted strip price per unit, next to a per-unit ceiling', () => {
    const v = describePriceCheck({
      ...base,
      comparison_status: 'COMPARED',
      price_basis: 'PER_STRIP',
      price_basis_label: 'per strip of 15',
      basis_source: 'DOCUMENT_LINE',
      basis_evidence: 'strip of 15',
      billed_unit_price: 2.2,
      is_overcharged: false,
      deviation_percentage: 0,
    });
    assert.strictEqual(v.verdict, 'within');
    assert.strictEqual(v.billed, '₹33.00 billed per strip of 15 → ₹2.20 per tablet');
    assert.strictEqual(v.ceiling, 'NPPA ceiling ₹2.30 per tablet');
    assert.match(v.basisNote ?? '', /bill line: “strip of 15”/);
  });

  it('never shows a verdict or percentage for an unknown basis', () => {
    const v = describePriceCheck({
      ...base,
      comparison_status: 'CANNOT_COMPARE',
      price_basis: 'UNKNOWN',
      price_basis_label: 'basis not stated',
      comparison_note: 'The document does not say whether this amount is for one tablet…',
    });
    assert.strictEqual(v.verdict, 'cannot_compare');
    assert.strictEqual(v.badge, 'Cannot compare reliably');
    assert.strictEqual(v.tone, 'warning');
    assert.doesNotMatch(v.badge + v.billed, /%|Within|Above/);
    assert.match(v.reason ?? '', /does not say/);
  });

  it('treats a response without price-basis fields as not compared, not as "within ceiling"', () => {
    // An older server (or a partial payload) must not be rendered as a fair price.
    const v = describePriceCheck({ ...base, is_overcharged: false, deviation_percentage: 0 });
    assert.strictEqual(v.verdict, 'cannot_compare');
  });

  it('labels an above-ceiling per-unit comparison with the server percentage', () => {
    const v = describePriceCheck({
      ...base,
      mrp: 22,
      nppa_ceiling_price: 20.1,
      comparison_status: 'COMPARED',
      price_basis: 'PER_UNIT',
      price_basis_label: 'per tablet',
      basis_source: 'DOCUMENT_HEADER',
      basis_evidence: 'Rx Rate per tablet/capsule (Rs)',
      billed_unit_price: 22,
      is_overcharged: true,
      deviation_percentage: 9.45,
    });
    assert.strictEqual(v.badge, 'Above ceiling (+9.45%)');
    assert.strictEqual(v.billed, '₹22.00 billed per tablet');
  });

  it('the manual check requires the person to say what the amount paid for', () => {
    const src = read('app', 'components', 'modules', 'DawaCheckView.tsx');
    assert.match(src, /price_basis: basis/);
    assert.match(src, /The amount is for…/);
    // The old example table mixed pack prices with invented per-pack "ceilings".
    assert.doesNotMatch(src, /nppaCeiling: 28\.5|Tablet \(15s\)/);
  });
});
