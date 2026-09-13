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

  test('schemesetu provisional-result disclosure vocabulary is fully localized', () => {
    const keys = [
      'criteriaEvaluated',
      'criteriaNotEvaluated',
      'provisionalNotice',
      'provisionallyEligible',
      'verificationNeeded',
      'notEligible',
      'howToClaim',
      'howToVerify',
      'nonDeterminative',
      'officialSources',
    ] as const;
    languages.forEach((lang) => {
      const schemesetu = translations[lang].modules.schemesetu;
      keys.forEach((key) => {
        assert.ok(
          schemesetu[key] && schemesetu[key].trim().length > 0,
          `Missing schemesetu.${key} in ${lang}`
        );
      });
    });
  });

  test('dawacheck dataset provenance disclosure is fully localized and keeps its placeholder', () => {
    languages.forEach((lang) => {
      const dawacheck = translations[lang].modules.dawacheck;
      assert.ok(
        dawacheck.dataSourceNotice && dawacheck.dataSourceNotice.trim().length > 0,
        `Missing dawacheck.dataSourceNotice in ${lang}`
      );
      assert.ok(
        dawacheck.dataSourceNotice.includes('{count}'),
        `dataSourceNotice in ${lang} lost its {count} placeholder`
      );
    });
  });
});

describe('Web Consent Vocabulary', () => {
  const languages: Language[] = ['en', 'hi', 'mr'];

  test('consent strings are localized in all 3 languages', () => {
    languages.forEach((lang) => {
      const upload = translations[lang].upload;
      assert.ok(
        upload.consentText && upload.consentText.trim().length > 0,
        `consentText missing in ${lang}`
      );
      assert.ok(
        upload.consentRequired && upload.consentRequired.trim().length > 0,
        `consentRequired missing in ${lang}`
      );
    });
  });
});

describe('Phase 3 Review and Disclosure Copy', () => {
  const phase3Languages: Language[] = ['en', 'hi', 'mr'];

  test('entity-resolution review strings exist in every language and name no unbuilt capability', () => {
    phase3Languages.forEach((lang) => {
      const review = translations[lang].resolution;
      Object.entries(review).forEach(([key, value]) => {
        assert.ok(value.trim().length > 0, `Empty resolution.${key} in ${lang}`);
        ['IndicSBERT', 'IndicXlit', 'FAISS'].forEach((claim) => {
          assert.ok(!value.includes(claim), `resolution.${key} in ${lang} names ${claim}`);
        });
      });
    });
  });

  test('heuristic probability disclosure and income opt-in copy exist in every language', () => {
    phase3Languages.forEach((lang) => {
      const modules = translations[lang].modules;
      assert.ok(modules.bimanyay.heuristicDisclosure.trim().length > 0, `Missing heuristicDisclosure in ${lang}`);
      for (const key of ['saveToCaseLabel', 'savedTriggered', 'savedNotReady', 'savedNoChange'] as const) {
        assert.ok(modules.schemesetu[key].trim().length > 0, `Missing schemesetu.${key} in ${lang}`);
      }
    });
  });
});
