// Completeness and safety checks for the Hindi and Marathi dictionaries (docs/localization.md).
// They show that nothing is missing or mangled. They say nothing about translation quality:
// that needs a native speaker.
import { describe, test } from 'node:test';
import assert from 'node:assert';
import { format, parseLanguage, translator } from '../app/i18n/format';
import { loadDictionary } from '../app/i18n/load';
import hi from '../app/i18n/locales/hi';
import mr from '../app/i18n/locales/mr';
import { localisedPublicCopy } from '../app/components/public/publicCopy';
import { allKeys, codeKeys } from '../scripts/i18n-keys';

const keys = allKeys();
const DICTIONARIES = { hi, mr } as const;

const placeholders = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort();
/** Figures as written: amounts, dates, counts, percentages. */
const figures = (s: string) => s.match(/\d+(?:[.,]\d+)*/g) ?? [];
/** Identifiers a patient may have to match against a document: CGHS, PM-JAY, IRDAI/HLT/… */
const identifiers = (s: string) => s.match(/\b[A-Z]{2,}(?:[-/][A-Z0-9]+)*\b/g) ?? [];

/**
 * All-capitals words that are right to translate: emphasis and headings (NOT, THIS PAGE,
 * INPATIENT BILL), and short forms with an everyday Hindi or Marathi wording (ASHA is आशा,
 * GR is शासन निर्णय, INR is रुपये, COI is conflict of interest, ID, FAQ, API).
 */
const ORDINARY_CAPITALS = new Set([
  'ADDRESS', 'API', 'ASHA', 'BILL', 'COI', 'DEMO', 'FAQ', 'GR', 'ID', 'ILLUSTRATIVE',
  'INPATIENT', 'INR', 'NOT', 'PAGE', 'THIS',
]);

describe('localisation', () => {
  test('the code only marks literal strings', () => {
    assert.deepEqual(codeKeys().dynamic, []);
  });

  for (const [lang, dictionary] of Object.entries(DICTIONARIES)) {
    test(`${lang}: every interface string has a translation`, () => {
      assert.deepEqual(keys.filter((k) => !dictionary[k]?.trim()), []);
    });

    test(`${lang}: no translation is left over from removed English text`, () => {
      const used = new Set(keys);
      assert.deepEqual(Object.keys(dictionary).filter((k) => !used.has(k)), []);
    });

    test(`${lang}: placeholders are the same as in English`, () => {
      const wrong = keys.filter((k) => dictionary[k] && String(placeholders(k)) !== String(placeholders(dictionary[k])));
      assert.deepEqual(wrong, []);
    });

    test(`${lang}: edge spaces are kept, so joined fragments do not run together`, () => {
      const wrong = keys.filter((k) => {
        const v = dictionary[k];
        return v !== undefined && (/^\s/.test(k) !== /^\s/.test(v) || /\s$/.test(k) !== /\s$/.test(v));
      });
      assert.deepEqual(wrong, []);
    });

    test(`${lang}: sentences are translated, not copied`, () => {
      const copied = keys.filter((k) => {
        const words = k.replace(/\{\w+\}/g, '').match(/\b[a-z]{3,}\b/g) ?? [];
        return words.length >= 4 && !/[ऀ-ॿ]/.test(dictionary[k] ?? '');
      });
      assert.deepEqual(copied, []);
    });

    test(`${lang}: figures and identifiers survive translation`, () => {
      const lost: string[] = [];
      for (const k of keys) {
        const v = dictionary[k];
        if (!v) continue;
        for (const token of [...figures(k), ...identifiers(k)]) {
          if (ORDINARY_CAPITALS.has(token) || v.includes(token)) continue;
          lost.push(`${token} :: ${k}`);
        }
      }
      assert.deepEqual(lost, []);
    });
  }

  test('public sections are translated even where they share a name with an identifier field', async () => {
    // `evidence` is both a list of evidence-state ids and a section of text.
    const copy = await localisedPublicCopy('hi');
    assert.match(copy.landing.evidence.heading, /[ऀ-ॿ]/);
    assert.match(copy.platform.evidence.provenanceHeading, /[ऀ-ॿ]/);
    assert.match(copy.platform.evidence.provenance[0].body, /[ऀ-ॿ]/);
    assert.match(copy.moduleSections.evidence, /[ऀ-ॿ]/);
    assert.deepEqual(copy.modules.billnyay.evidence, (await localisedPublicCopy('en')).modules.billnyay.evidence);
  });

  test('a missing key falls back to the English sentence', () => {
    assert.equal(translator(hi)('A sentence nobody translated {n}', { n: 2 }), 'A sentence nobody translated 2');
    assert.equal(translator(undefined)('Delete this case'), 'Delete this case');
  });

  test('placeholders are filled, and unknown ones are left visible', () => {
    assert.equal(format('{a} and {b}', { a: 1 }), '1 and {b}');
  });

  test('each language loads its own dictionary and English loads none', async () => {
    assert.equal(await loadDictionary('en'), undefined);
    assert.equal(await loadDictionary('hi'), hi);
    assert.equal(await loadDictionary('mr'), mr);
    assert.equal(parseLanguage('fr'), 'en');
  });
});
