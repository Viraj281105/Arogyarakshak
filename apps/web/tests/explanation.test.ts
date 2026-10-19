import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { describeExplanation, Explanation } from '../app/lib/explanation';
import { EXPLAIN_STRINGS } from '../app/lib/explainStrings';

const base: Explanation = {
  finding_type: 'BILLNYAY_LINE',
  headline: 'Charged 500, reference 350',
  evidence: [
    { label: 'Bill line', value: 'Consultation', provenance: 'OCR_EXTRACTED', document: 'bill.pdf', source_text: null },
    { label: 'Amount', value: null, provenance: 'OCR_EXTRACTED', document: null, source_text: null },
    { label: 'Price', value: '3', provenance: 'USER_ENTERED', document: null, source_text: null },
  ],
  rules: [
    {
      kind: 'REFERENCE_TABLE_ROW',
      name: 'CGHS row',
      source: 'CGHS 2024',
      facts: [
        { label: 'Rate', value: '₹350' },
        { label: 'CGHS procedure code', value: null },
      ],
    },
  ],
  trust: { code: 'MACHINE_READ_LINE', label: 'Machine-read bill line', detail: null },
  undetermined: [{ code: 'X', reason: 'Not checked.' }],
  not_recorded: ['CGHS procedure code'],
  generated_by: 'deterministic',
  disclaimer: 'd',
};

describe('explanation view (ADR-017)', () => {
  it('shows unrecorded values as "not recorded", never blank or invented', () => {
    const v = describeExplanation(base, 'en');
    assert.strictEqual(v.evidence[1].value, 'not recorded');
    assert.strictEqual(v.rules[0].facts[1].value, 'not recorded');
    assert.strictEqual(v.rules[0].facts[1].recorded, false);
    assert.strictEqual(v.rules[0].facts[0].recorded, true);
  });

  it('only OCR/LLM-derived evidence needs a document; user-entered evidence has none to show', () => {
    const v = describeExplanation(base, 'en');
    assert.strictEqual(v.evidence[0].document, 'bill.pdf');
    assert.strictEqual(v.evidence[1].document, 'not recorded');
    assert.strictEqual(v.evidence[2].document, null);
  });

  it('maps provenance classes to labels and falls back to "origin not recorded"', () => {
    const v = describeExplanation({ ...base, evidence: [{ ...base.evidence[0], provenance: 'SOMETHING_NEW' }] }, 'en');
    assert.strictEqual(v.evidence[0].provenance, EXPLAIN_STRINGS.en.provenance.NOT_RECORDED);
  });

  it('localises the fixed labels in hi/mr while keeping server text as received', () => {
    const v = describeExplanation(base, 'hi');
    assert.strictEqual(v.evidence[1].value, EXPLAIN_STRINGS.hi.notRecorded);
    assert.strictEqual(v.headline, base.headline);
  });

  it('has complete hi/mr strings, flagged for native-speaker QA', () => {
    const keys = Object.keys(EXPLAIN_STRINGS.en).sort();
    for (const lang of ['hi', 'mr'] as const) {
      assert.deepStrictEqual(Object.keys(EXPLAIN_STRINGS[lang]).sort(), keys);
      assert.deepStrictEqual(
        Object.keys(EXPLAIN_STRINGS[lang].provenance).sort(),
        Object.keys(EXPLAIN_STRINGS.en.provenance).sort(),
      );
    }
    const src = readFileSync('app/lib/explainStrings.ts', 'utf-8');
    assert.strictEqual((src.match(/NEEDS NATIVE-SPEAKER QA/g) ?? []).length >= 2, true);
  });
});
