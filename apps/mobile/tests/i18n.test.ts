// Hindi and Marathi completeness for the mobile app (docs/localization.md). These checks show
// that nothing user-facing bypasses translation and nothing is mangled. They say nothing about
// translation quality: that needs a native speaker.
import { describe, test } from 'node:test';
import assert from 'node:assert';
import type { GrievanceTimelineEvent } from '../src/api/types';
import { checklistSummary, stepCountText } from '../src/components/ui/logic';
import { explanationToText } from '../src/services/explanation';
import { humanizeEnum } from '../src/services/labels';
import { setLanguage } from '../src/services/languageStore';
import { describePriceCheck } from '../src/services/priceCheck';
import { planSlaReminders } from '../src/services/slaReminders';
import { format, tr } from '../src/translations/tr';
import { UI } from '../src/translations/ui';
import { codeKeys, unsubscribedComponents, untranslated } from './i18nScan';

const { keys, dynamicMsg } = codeKeys();
const LANGS = [
  ['hi', 0],
  ['mr', 1],
] as const;

const placeholders = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort();
const figures = (s: string) => s.match(/\d+(?:[.,]\d+)*/g) ?? [];

describe('mobile localisation', () => {
  test('no user-facing English bypasses translation', () => {
    assert.deepEqual(untranslated().map((f) => `${f.file}:${f.line} ${f.kind} ${f.value}`), []);
  });

  test('every component that renders tr() text redraws on a language change', () => {
    assert.deepEqual(unsubscribedComponents(), []);
  });

  test('the code only marks literal strings with msg()', () => {
    assert.deepEqual(dynamicMsg, []);
  });

  test('the dictionary has no entry the code stopped using', () => {
    const used = new Set(keys);
    assert.deepEqual(Object.keys(UI).filter((k) => !used.has(k)), []);
  });

  for (const [lang, index] of LANGS) {
    test(`${lang}: every marked string has a translation`, () => {
      assert.deepEqual(keys.filter((k) => !UI[k]?.[index]?.trim()), []);
    });

    test(`${lang}: placeholders, edge spaces and figures survive`, () => {
      const wrong = keys.filter((k) => {
        const v = UI[k]?.[index];
        if (!v) return false;
        return (
          String(placeholders(k)) !== String(placeholders(v)) ||
          /^\s/.test(k) !== /^\s/.test(v) ||
          /\s$/.test(k) !== /\s$/.test(v) ||
          figures(k).some((n) => !v.includes(n))
        );
      });
      assert.deepEqual(wrong, []);
    });

    test(`${lang}: sentences are translated, not copied`, () => {
      const copied = keys.filter((k) => {
        const words = k.replace(/\{\w+\}/g, '').match(/\b[a-z]{3,}\b/g) ?? [];
        return words.length >= 4 && !/[ऀ-ॿ]/.test(UI[k]?.[index] ?? '');
      });
      assert.deepEqual(copied, []);
    });
  }

  test('wording built outside components follows the chosen language', () => {
    // These keep English in constants or build it from values, so the scan alone cannot show
    // that it is translated by the time it reaches the screen.
    setLanguage('hi');
    const shown = [
      humanizeEnum('COMPLETED'),
      stepCountText(0, 3),
      checklistSummary([{ status: 'done' }]),
      describePriceCheck({ active_ingredient: 'x', mrp: 33, nppa_ceiling_price: 2.3, is_overcharged: null, deviation_percentage: null }).reason ?? '',
      planSlaReminders(
        [{ tier: 'LEVEL_1_GRO', status: 'ACTIVE', deadline_date: '2099-01-20' } as GrievanceTimelineEvent],
        new Date(2098, 0, 1),
      )[0].body,
      explanationToText({
        finding_type: 't', headline: 'h', trust: { code: 'c', label: 'l', detail: null }, rules: [], undetermined: [], not_recorded: [],
        generated_by: 'rules', disclaimer: 'd',
        evidence: [{ label: 'a', value: null, provenance: 'USER_ENTERED', document: null, source_text: null }],
      }),
    ];
    setLanguage('en');
    for (const text of shown) assert.match(text, /[ऀ-ॿ]/);
    assert.equal(humanizeEnum('COMPLETED'), 'Review completed');
  });

  test('tr follows the chosen language and falls back to English', () => {
    const [key] = keys;
    setLanguage('hi');
    assert.equal(tr(key), format(UI[key][0]));
    setLanguage('mr');
    assert.equal(tr(key), format(UI[key][1]));
    assert.equal(tr('A sentence nobody translated {n}', { n: 2 }), 'A sentence nobody translated 2');
    setLanguage('en');
    assert.equal(tr(key), key);
  });
});
