import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { buildBenchmarkRequest, describePriceCheck } from '../src/services/priceCheck';

const read = (...p: string[]) => readFileSync(join(process.cwd(), ...p), 'utf-8');

describe('DawaCheck price basis (mobile)', () => {
  it('requires the person to say what the amount paid for', () => {
    const r = buildBenchmarkRequest('Dolo 650', '33', null, '');
    assert.strictEqual(r.ok, false);
    if (!r.ok) assert.match(r.error, /what the amount paid for/);
  });

  it('requires a whole, positive pack size for a strip price', () => {
    for (const bad of ['', '0', '-3', '2.5', 'abc']) {
      const r = buildBenchmarkRequest('Dolo 650', '33', 'PER_STRIP', bad);
      assert.strictEqual(r.ok, false, `pack size "${bad}" must be refused`);
    }
    const ok = buildBenchmarkRequest('Dolo 650', '33', 'PER_STRIP', '15');
    assert.deepStrictEqual(ok, { ok: true, body: { brand_name: 'Dolo 650', mrp: 33, price_basis: 'PER_STRIP', units_per_pack: 15 } });
  });

  it('sends a line total with its quantity, and a unit price with nothing else', () => {
    const total = buildBenchmarkRequest('Dolo 650', '25', 'LINE_TOTAL', '10');
    assert.ok(total.ok && total.body.quantity === 10 && total.body.units_per_pack === undefined);
    const unit = buildBenchmarkRequest('Dolo 650', '2.1', 'PER_UNIT', '99');
    assert.ok(unit.ok && unit.body.units_per_pack === undefined && unit.body.quantity === undefined);
  });

  it('never shows a verdict for an uncompared price', () => {
    const v = describePriceCheck({
      active_ingredient: 'Paracetamol 650mg',
      mrp: 33,
      nppa_ceiling_price: 2.3,
      is_overcharged: null,
      deviation_percentage: null,
      comparison_status: 'CANNOT_COMPARE',
      comparison_note: 'The document does not say…',
      unit_label: 'tablet',
    });
    assert.strictEqual(v.badge, 'Cannot compare reliably');
    assert.strictEqual(v.variant, 'warning');
    assert.doesNotMatch(v.badge, /%|Within|Above/);
  });

  it('shows the converted per-unit price next to the per-unit ceiling', () => {
    const v = describePriceCheck({
      active_ingredient: 'Paracetamol 650mg',
      mrp: 33,
      nppa_ceiling_price: 2.3,
      is_overcharged: false,
      deviation_percentage: 0,
      comparison_status: 'COMPARED',
      price_basis: 'PER_STRIP',
      price_basis_label: 'per strip of 15',
      billed_unit_price: 2.2,
      unit_label: 'tablet',
    });
    assert.strictEqual(v.billed, '₹33.00 billed per strip of 15 → ₹2.20 per tablet');
    assert.strictEqual(v.verdict, 'within');
  });

  it('quick samples declare what their price buys (no strip price sent as a tablet price)', () => {
    const src = read('src', 'screens', 'DawaCheckScreen.tsx');
    assert.doesNotMatch(src, /mrp: '33\.5' \}/, 'the old undeclared (15s) strip sample is gone');
    const samples = src.match(/\{ name: '[^']+', mrp: '[^']+', basis: '[A-Z_]+'/g) ?? [];
    assert.strictEqual(samples.length, 4);
  });
});
