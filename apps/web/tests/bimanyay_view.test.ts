import { describe, it } from 'node:test';
import assert from 'node:assert';
import { translations } from '../app/translations';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { viewSource } from './viewSource';

// The reversal score is a fixed rule prior per denial category (bimanyay.clause_auditor),
// not a probability from past outcomes — no historical dataset exists (#90).
describe('BimaNyay never presents its rule score as a probability', () => {
  const src = viewSource('BimaNyayView');

  it('the English label does not call it a probability or likelihood', () => {
    assert.ok(!/probability|likelihood/i.test(translations.en.modules.bimanyay.reversalScore));
  });

  it('the score is shown out of 100 with the heuristic disclosure always rendered', () => {
    // The score lives in DisputeSummary; the form's "share of the claim denied" is a real percentage.
    const src = readFileSync(join(process.cwd(), 'app', 'components', 'modules', 'bimanyay', 'DisputeSummary.tsx'), 'utf-8');
    // A rendered "NN%" text node (a CSS width like `${score}%` is fine).
    assert.ok(!/>\s*\{[^}]*\}%\s*</.test(src) && !/toFixed\(0\)\}%/.test(src), 'no percentage headline');
    assert.ok(/<p className="bn-fine">\{t\.heuristicDisclosure\}<\/p>/.test(src), 'disclosure must not be conditional');
  });

  it('deadlines say they are counted from today', () => {
    assert.ok(/Counted from today/.test(src));
  });
});
