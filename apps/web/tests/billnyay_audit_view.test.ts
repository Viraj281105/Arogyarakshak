import { describe, it } from 'node:test';
import assert from 'node:assert';
import { composeAudit } from '../app/components/modules/billnyay/AuditResults';
import type { AuditResultItem } from '../app/components/modules/billnyay/types';

const line = (p: Partial<AuditResultItem>): AuditResultItem => ({
  item_name: 'x', charged: 0, cghs_benchmark: null, deviation_percentage: 0, is_deviation: false,
  benchmarked: false, status: 'not_benchmarked', ...p,
});

describe('BillNyay audit composition chart', () => {
  it('splits each rupee by line status and never counts an unmatched line as compared', () => {
    const c = composeAudit([
      line({ charged: 1800, cghs_benchmark: 700, benchmarked: true, status: 'overcharged', is_deviation: true }),
      line({ charged: 13500, cghs_benchmark: 13500, benchmarked: true, status: 'within_benchmark' }),
      line({ charged: 4500, cghs_benchmark: 0, benchmarked: true, status: 'bundled', is_deviation: true }),
      line({ charged: 500 }),
      // matched a row but could not be compared (no unit count): not compared, not fair
      line({ charged: 2000, cghs_benchmark: null, benchmarked: false, status: 'not_benchmarked' }),
    ]);
    assert.deepStrictEqual(c, { within: 14200, above: 1100, bundled: 4500, notCompared: 2500 });
  });

  it('a line billed below its reference does not offset another line', () => {
    const c = composeAudit([
      line({ charged: 100, cghs_benchmark: 500, benchmarked: true, status: 'within_benchmark' }),
      line({ charged: 900, cghs_benchmark: 400, benchmarked: true, status: 'overcharged', is_deviation: true }),
    ]);
    assert.strictEqual(c.above, 500);
    assert.strictEqual(c.within, 500);
  });
});
