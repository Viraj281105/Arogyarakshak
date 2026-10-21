import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const src = readFileSync(join(process.cwd(), 'app', 'components', 'modules', 'SchemeSetuView.tsx'), 'utf-8');

describe('SchemeSetu form and explainer', () => {
  it('the state select starts on an empty placeholder, so what is shown is what is sent', () => {
    // Regression: state was "" while the select displayed its first option (Maharashtra).
    assert.ok(/useState\(""\);\s*\n\s*const \[category/.test(src) || /const \[state, setState\] = useState\(""\)/.test(src));
    assert.ok(/<option value="" disabled>/.test(src));
  });

  it('category is only sent when chosen; medical need does not block the check', () => {
    assert.ok(/\.\.\.\(category \? \{ category \} : \{\}\)/.test(src));
    assert.ok(!/!medicalNeed\.trim\(\)/.test(src));
  });

  it('the pre-check explainer states only facts sourced in schemesetu/thresholds.py', () => {
    assert.ok(!src.includes('1,356'), 'procedure count has no source in the repo');
    assert.ok(/Source: \{s\.source\}/.test(src));
  });
});
