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
