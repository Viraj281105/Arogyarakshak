import { test, describe } from 'node:test';
import assert from 'node:assert';
import { translations, Language } from '../app/translations';

describe('Web Trilingual Localization Integrity', () => {
  const languages: Language[] = ['en', 'hi', 'mr'];
  const expectedModules = ['billnyay', 'bimanyay', 'daavisetu', 'schemesetu', 'dawacheck'] as const;

  test('should have entries for all supported languages', () => {
    languages.forEach((lang) => {
      assert.ok(translations[lang], `Missing translation object for language: ${lang}`);
      assert.ok(translations[lang].appName, `Missing appName in ${lang}`);
      assert.ok(translations[lang].byodBadge, `Missing byodBadge in ${lang}`);
    });
  });

  test('should have all 5 modules defined with titles and descriptions across all languages', () => {
    languages.forEach((lang) => {
      const dict = translations[lang];
      expectedModules.forEach((mod) => {
        const moduleData = dict.modules[mod];
        assert.ok(moduleData, `Missing module ${mod} in ${lang}`);
        assert.ok(moduleData.title && moduleData.title.trim().length > 0, `Empty title for ${mod} in ${lang}`);
        assert.ok(moduleData.desc && moduleData.desc.trim().length > 0, `Empty desc for ${mod} in ${lang}`);
      });
    });
  });

  test('should have consistent upload and streaming progress labels across all languages', () => {
    languages.forEach((lang) => {
      const dict = translations[lang];
      assert.ok(dict.upload.zeroRetentionNotice, `Missing zeroRetentionNotice in ${lang}`);
      assert.ok(dict.stream.agentOrchestration, `Missing agentOrchestration in ${lang}`);
      assert.ok(dict.stream.stepOcr, `Missing stepOcr in ${lang}`);
      assert.ok(dict.stream.stepEntities, `Missing stepEntities in ${lang}`);
      assert.ok(dict.stream.stepAudit, `Missing stepAudit in ${lang}`);
      assert.ok(dict.stream.stepComplete, `Missing stepComplete in ${lang}`);
    });
  });
});

describe('Web UI Capability Claim Integrity', () => {
  const languages: Language[] = ['en', 'hi', 'mr'];

  // Capabilities that do not exist in the codebase. The upload pipeline runs
  // OCR -> Kadi entity extraction -> DB write. It performs no transliteration, no
  // IndicSBERT/IndicXlit entity resolution, no CGHS audit and no grievance packaging.
  const unimplementedClaims = [
    'IndicSBERT',
    'IndicXlit',
    'Transliteration',
    'लिप्यंतरण',
    'FAISS',
  ];

  test('pipeline stage labels must not advertise unimplemented capabilities', () => {
    languages.forEach((lang) => {
      const stream = translations[lang].stream;
      const labels = [
        stream.statusHeading,
        stream.stepOcr,
        stream.stepEntities,
        stream.stepAudit,
        stream.stepComplete,
      ];
      labels.forEach((label) => {
        unimplementedClaims.forEach((claim) => {
          assert.ok(
            !label.toLowerCase().includes(claim.toLowerCase()),
            `Stage label in "${lang}" claims unimplemented capability "${claim}": ${label}`
          );
        });
      });
    });
  });

  test('upload action labels must not claim a multi-agent audit runs on upload', () => {
    languages.forEach((lang) => {
      const upload = translations[lang].upload;
      [upload.processBtn, upload.processing].forEach((label) => {
        assert.ok(
          !/multi-?agent/i.test(label),
          `Upload label in "${lang}" claims a multi-agent audit on upload: ${label}`
        );
      });
    });
  });

  test('every stage label is non-empty in all languages', () => {
    languages.forEach((lang) => {
      const stream = translations[lang].stream;
      (['statusHeading', 'stepOcr', 'stepEntities', 'stepAudit', 'stepComplete'] as const).forEach(
        (key) => {
          assert.ok(
            stream[key] && stream[key].trim().length > 0,
            `Empty stream.${key} in ${lang}`
          );
        }
      );
    });
  });

  test('billnyay audit status vocabulary is fully localized', () => {
    const keys = [
      'notBenchmarked',
      'withinBenchmark',
      'notBenchmarkedBadge',
      'overchargedBadge',
      'bundledBadge',
      'fairBadge',
      'unmatchedNotice',
    ] as const;

    languages.forEach((lang) => {
      const billnyay = translations[lang].modules.billnyay;
      keys.forEach((key) => {
        assert.ok(
          billnyay[key] && billnyay[key].trim().length > 0,
          `Missing billnyay.${key} in ${lang}`
        );
      });
      // The notice must keep both interpolation placeholders.
      assert.ok(
        billnyay.unmatchedNotice.includes('{count}') && billnyay.unmatchedNotice.includes('{amount}'),
        `unmatchedNotice in ${lang} lost its {count}/{amount} placeholders`
      );
    });
  });
});
