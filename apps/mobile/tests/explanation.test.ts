import { describe, it } from 'node:test';
import assert from 'node:assert';
import { Explanation, explanationToText } from '../src/services/explanation';

const exp: Explanation = {
  finding_type: 'BILLNYAY_LINE',
  headline: 'Charged 500, reference 350',
  evidence: [
    { label: 'Bill line', value: 'Consultation', provenance: 'OCR_EXTRACTED', document: null, source_text: null },
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
  not_recorded: [],
  generated_by: 'deterministic',
  disclaimer: 'Not advice.',
};

describe('explanationToText (ADR-015)', () => {
  const text = explanationToText(exp);
  it('says "not recorded" for unrecorded facts and missing documents', () => {
    assert.match(text, /CGHS procedure code: not recorded/);
    assert.match(text, /Bill line: Consultation \(read from your document\) · document: not recorded/);
  });
  it('does not demand a document for user-entered evidence', () => {
    assert.match(text, /Price: 3 \(entered by you\)\n/);
  });
  it('lists what could not be determined and states no model wrote it', () => {
    assert.match(text, /• Not checked\./);
    assert.match(text, /no AI model/);
  });
});
