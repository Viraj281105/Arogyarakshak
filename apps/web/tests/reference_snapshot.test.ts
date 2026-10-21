import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  CGHS_CATEGORY_COUNTS,
  CGHS_EXAMPLE_RATES,
  CGHS_TOTAL_ROWS,
  CGHS_VERSION,
  LAW_LIBRARY,
  NPPA_REFERENCE_FORMULATIONS,
} from '../app/lib/referenceSnapshot';
import { ILLUSTRATIVE_LINES, composeBill } from '../app/lib/illustrativeBill';

// The landing page shows these figures as facts about the build, so they must match the data.
const repo = join(process.cwd(), '..', '..');
const readJson = (...p: string[]) => JSON.parse(readFileSync(join(repo, ...p), 'utf-8'));

describe('Landing-page reference figures match the shipped reference data', () => {
  const cghs = readJson('packages', 'billnyay', 'billnyay', 'data', 'cghs_rates.json');
  const rates = cghs.rates as Record<string, { name: string; benchmark_rate: number; category: string; bundled: boolean; billing_unit: string }>;

  it('CGHS version and row counts per category', () => {
    assert.strictEqual(cghs.version, CGHS_VERSION);
    assert.strictEqual(Object.keys(rates).length, CGHS_TOTAL_ROWS);
    const counts: Record<string, number> = {};
    for (const r of Object.values(rates)) counts[r.category] = (counts[r.category] ?? 0) + 1;
    assert.deepStrictEqual(
      Object.fromEntries(CGHS_CATEGORY_COUNTS.map((c) => [c.category, c.rows])),
      counts,
    );
  });

  it('the illustrative bill uses the real CGHS rows', () => {
    for (const r of Object.values(CGHS_EXAMPLE_RATES)) {
      const row = rates[r.key];
      assert.ok(row, r.key);
      assert.strictEqual(row.name, r.name);
      assert.strictEqual(row.benchmark_rate, r.rate);
      assert.strictEqual(row.billing_unit, r.unit);
      assert.strictEqual(row.bundled, r.bundled);
    }
  });

  it('law library size and verified count', () => {
    const law = readJson('packages', 'billnyay', 'billnyay', 'data', 'law_library.json') as { verification_status: string }[];
    assert.strictEqual(law.length, LAW_LIBRARY.total);
    assert.strictEqual(law.filter((l) => l.verification_status === 'verified').length, LAW_LIBRARY.verified);
  });

  it('the illustrative bill follows the BillNyay status rule and adds up', () => {
    assert.deepStrictEqual(
      Object.fromEntries(ILLUSTRATIVE_LINES.map((l) => [l.id, l.status])),
      { ward: 'overcharged', nursing: 'bundled', cbc: 'overcharged', xray: 'within_benchmark', kit: 'not_benchmarked' },
    );
    const c = composeBill(ILLUSTRATIVE_LINES);
    assert.strictEqual(c.withinReference + c.aboveReference + c.bundled + c.notCompared, c.billed);
    assert.deepStrictEqual(c, { billed: 11150, withinReference: 5100, aboveReference: 3050, bundled: 1800, notCompared: 1200 });
  });

  it('NPPA reference formulation count', () => {
    const src = readFileSync(join(repo, 'packages', 'dawacheck', 'dawacheck', 'reference_data.py'), 'utf-8');
    const block = src.slice(src.indexOf('NPPA_REFERENCE_DATA'));
    const body = block.slice(0, block.indexOf('\n}\n'));
    assert.strictEqual((body.match(/^ {4}"[^"]+": \{/gm) ?? []).length, NPPA_REFERENCE_FORMULATIONS);
  });
});
