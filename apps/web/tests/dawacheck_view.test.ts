import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const read = (...p: string[]) => readFileSync(join(process.cwd(), ...p), 'utf-8');

describe('DawaCheck view', () => {
  const view = read('app', 'components', 'modules', 'DawaCheckView.tsx');
  const bar = read('app', 'components', 'modules', 'dawacheck', 'PriceBar.tsx');

  it('does not state the unverified DPCO provision as settled law', () => {
    // law_library.json marks "NPPA DPCO 2013 — Paragraph 14(1)" as unverified.
    assert.ok(!/is an offence under the Essential Commodities Act/.test(view));
    assert.ok(!/must mandatorily display/.test(view));
    assert.ok(/has not yet verified/.test(view));
  });

  it('the price bar draws a paid-per-unit bar only for a comparison the server made', () => {
    assert.ok(/view\.verdict === "cannot_compare" \? null/.test(bar));
  });

  it('the manual result shows where the price basis came from', () => {
    assert.ok(/price\.basisNote/.test(view));
  });
});
